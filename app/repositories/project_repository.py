from typing import Any
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_database


COLLECTION_NAME = "projects"


def _get_collection() -> AsyncIOMotorCollection:
    db = get_database()
    return db[COLLECTION_NAME]


async def upsert_project(project: dict[str, Any]) -> None:
    collection = _get_collection()
    identifier = project.get("project_id") or project.get("url")
    if not identifier:
        raise ValueError("Project data is missing project_id or url field")
    query_field = "project_id" if project.get("project_id") else "url"
    await collection.update_one({query_field: identifier}, {"$set": project}, upsert=True)


async def list_projects(limit: int | None = None) -> list[dict[str, Any]]:
    collection = _get_collection()
    cursor = collection.find().sort("_id", -1)
    if limit is not None:
        cursor = cursor.limit(limit)
    results = []
    async for doc in cursor:
        # 将 ObjectId 转为字符串，避免响应序列化失败
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results