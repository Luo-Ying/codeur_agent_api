from typing import Any
from motor.motor_asyncio import AsyncIOMotorCollection  # pyright: ignore[reportMissingImports]

from app.db.mongo import get_database
from app.services.globalVars import ProjectStatus


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
        # convert ObjectId to string to avoid response serialization failure
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


async def get_project_by_url(url: str) -> dict[str, Any] | None:
    collection = _get_collection()
    return await collection.find_one({"url": url})

async def update_project_status(project_id: str, status: ProjectStatus | str) -> None:
    collection = _get_collection()
    await collection.update_one({"project_id": project_id}, {"$set": {"status": status.value if isinstance(status, ProjectStatus) else status}})