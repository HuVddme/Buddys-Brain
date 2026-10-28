"""Shared fixed-window limits for expensive public operations.

Reservations count attempts, including failed work. Mongo's unique _id index and
conditional atomic updates enforce limits across processes and restarts.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import os

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from .database import usage_collection


def configured_limit(name, default):
    try:
        value = int(os.getenv(name, str(default)))
        if value < 0:
            raise ValueError
        return value
    except ValueError as exc:
        raise HTTPException(503, "Live usage limits are not configured correctly.",
                            headers={"X-Error-Code": "usage_unavailable"}) from exc


class UsageLimiter:
    def __init__(self, collection):
        self.collection = collection
        self.index_ready = False

    async def reserve(self, cost=1, now=None):
        if cost < 1:
            raise ValueError("Reservation cost must be positive")
        minute_limit = configured_limit("LIVE_REQUESTS_PER_MINUTE", 12)
        daily_limit = configured_limit("LIVE_REQUESTS_PER_DAY", 100)
        now = now or datetime.now(timezone.utc)
        minute = now.replace(second=0, microsecond=0)
        day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        windows = [
            ("minute", minute, minute + timedelta(minutes=1), minute_limit,
             "Live requests are busy. Please try again shortly."),
            ("day", day, day + timedelta(days=1), daily_limit,
             "Today's live allowance is used up. Explore the demo or try again after midnight UTC."),
        ]
        try:
            # Include index initialization and both reservations in one deadline.
            async with asyncio.timeout(5):
                if not self.index_ready:
                    await self.collection.create_index("expires_at", expireAfterSeconds=0)
                    self.index_ready = True
                for label, start, end, limit, message in windows:
                    remaining_seconds = max(1, int((end - now).total_seconds()) + 1)
                    headers = {"Retry-After": str(remaining_seconds),
                               "X-Error-Code": f"{label}_limit"}
                    if cost > limit:
                        raise HTTPException(429, message, headers=headers)
                    query = {"_id": f"global:{label}:{start.isoformat()}",
                             "count": {"$lte": limit - cost}}
                    update = {"$inc": {"count": cost},
                              "$setOnInsert": {"expires_at": end + timedelta(days=1)}}
                    try:
                        reservation = await self.collection.find_one_and_update(
                            query, update, upsert=True, return_document=ReturnDocument.AFTER,
                        )
                    except DuplicateKeyError:
                        # A competing initial insert may still leave capacity.
                        # Retry only the conditional update; never exceed the cap.
                        reservation = await self.collection.find_one_and_update(
                            query, update, upsert=False, return_document=ReturnDocument.AFTER,
                        )
                    if reservation is None:
                        raise HTTPException(429, message, headers=headers)
        except (PyMongoError, TimeoutError) as exc:
            logging.getLogger(__name__).warning("Usage reservation failed (%s)", type(exc).__name__)
            raise HTTPException(503, "Live requests are temporarily unavailable. Explore the demo or try again later.",
                                headers={"X-Error-Code": "usage_unavailable"}) from exc


limiter = UsageLimiter(usage_collection)


async def reserve_request():
    await limiter.reserve()
