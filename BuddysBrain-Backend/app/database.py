import os
from . import config  # noqa: F401
from motor.motor_asyncio import AsyncIOMotorClient


MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
MONGO_DB = os.getenv("MONGO_DB")

MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/{MONGO_DB}?retryWrites=true&w=majority"

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]
collection = db["resources"]
