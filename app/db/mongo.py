import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient  # pyright: ignore[reportMissingImports]
from urllib.parse import urlparse


_mongo_client: Optional[AsyncIOMotorClient] = None
_db_name: Optional[str] = None


def _extract_db_name(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.path and parsed.path != "/":
        return parsed.path.lstrip("/")
    raise ValueError("MongoDB URI is missing database name")


def _get_mongo_uri() -> str:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("Environment variable MONGODB_URI is not set")
    return uri


async def connect_to_mongo() -> None:
    global _mongo_client, _db_name
    if _mongo_client is not None:
        return
    uri = _get_mongo_uri()
    _mongo_client = AsyncIOMotorClient(uri)
    _db_name = _extract_db_name(uri)


async def close_mongo_connection() -> None:
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None


def get_database():
    if _mongo_client is None or _db_name is None:
        raise RuntimeError("MongoDB is not initialized, please call connect_to_mongo first")
    return _mongo_client[_db_name]