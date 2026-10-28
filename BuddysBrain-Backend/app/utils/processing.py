from functools import lru_cache
import os
import logging

from fastapi import HTTPException
from openai import APITimeoutError, OpenAI
from starlette.concurrency import run_in_threadpool

from .. import config  # noqa: F401


class ProcessingError(Exception):
    """A safe, user-facing processing failure; never a document summary."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


@lru_cache(maxsize=1)
def get_ai_client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ProcessingError("AI processing is not configured.", 503)
    return OpenAI(api_key=key, timeout=30.0, max_retries=1)


async def run_processing(function, *args, **kwargs):
    """Keep synchronous SDKs and CPU work off the ASGI event loop."""
    try:
        return await run_in_threadpool(function, *args, **kwargs)
    except ProcessingError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except APITimeoutError as exc:
        raise HTTPException(504, "AI processing timed out. Please try again.") from exc
    except Exception as exc:
        # Provider errors may contain credentials, URLs or document text.
        logging.getLogger(__name__).warning("%s failed (%s)", function.__name__, type(exc).__name__)
        raise HTTPException(502, "Processing failed. Please try again later.") from exc
