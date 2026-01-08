import logging
from typing import Any
from fastapi import FastAPI # pyright: ignore[reportMissingImports]
import os
from dotenv import load_dotenv

from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.services.mailBox import Email, MailBox, MailConnection, MailConnectionConfig
from app.utils.findMatchedProject import is_matched_project
from app.utils.buildObjectProject import build_object_project
from app.repositories.project_repository import (
    delete_all_projects,
    delete_project_by_url as delete_project_record,
    get_project_by_url,
    get_projects_count_from_repo,
    list_projects,
    upsert_project,
    update_project_record,
)
from app.services.globalVars import ProjectStatus
from app.utils.applyForProject import apply_for_project
from app.utils.someCommonFunctions import extract_projectUrl_from_emailcontent

logger = logging.getLogger(__name__)

app = FastAPI()

load_dotenv()
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.get("/get_codeur_new_project_matched")
async def get_codeur_new_project_matched() -> list[dict]:
    mail_box = MailBox(MailConnection(MailConnectionConfig(
        host="imap.gmail.com", 
        port=993, 
        username=EMAIL_USERNAME, 
        password=EMAIL_PASSWORD
    )))
    mail_box.open()
    unread_emails = mail_box.getListUnreadEmails()
    project_list: list[dict] = []

    # filter emails by email_from and email_title and is_matched_project
    for email_id in unread_emails:
        email = mail_box.getEmail(email_id)
        if not email:
            logger.warning(f"cannot get email content for email UID {email_id}")
            continue
        email_obj = Email(email)
        try:
            email_title, email_from, email_content = email_obj.parse_email()
        except ValueError as exc:
            logger.warning(f"parse email UID {email_id} failed: {exc}")
            continue
        if "notification@compte.codeur.com" not in email_from or "Nouveau projet" not in email_title:
            continue
        project_url = extract_projectUrl_from_emailcontent(email_content)
        if project_url is None:
            logger.warning(f"cannot extract project URL from email content for email UID {email_id}")
            continue
        existing = await get_project_by_url(project_url)
        if existing:
            logger.warning(f"project {project_url} already exists")
            mail_box.setEmailSeen(email_id)
            mail_box.moveEmailToLabel(email_id, "Codeur")
            continue
        # if the current email is matched (i.e. passed all previous continues), move it to the label "Codeur"
        is_matched = is_matched_project(email_content)
        logger.info(f"project {project_url} is matched: {is_matched}")
        if not is_matched:
            logger.warning(f"project {project_url} is not matched")
            mail_box.deleteEmailFromInbox(email_id)
            continue
        project, is_project_available = build_object_project(email_content)
        if not is_project_available:
            logger.warning(f"project {project_url} is not available")
            mail_box.setEmailSeen(email_id)
            mail_box.moveEmailToLabel(email_id, "Codeur")
            continue
        if is_project_available and project is not None:
            logger.info(f"build object project {project_url} successfully")
            project_dict = project.__dict__
            project_list.append(project_dict)
            await upsert_project(project_dict)
            mail_box.setEmailSeen(email_id)
            mail_box.moveEmailToLabel(email_id, "Codeur")

    mail_box.close()
    return project_list

@app.get("/projects/apply_all_projects")
async def apply_all_projects() -> list[dict]:
    projects = await list_projects()
    for project in projects:
        if project.status != ProjectStatus.NEW:
            continue
        result, message = await apply_for_project(project)
        if not result:
            logger.error(f"Apply project {project.url} failed: {message}")
            continue
        logger.info(f"Apply project {project.url} successfully: {message}")

@app.get("/projects/apply_project")
async def apply_project(project_url: str) -> dict:
    logger.info(f"Apply project: {project_url}")
    project = await get_project_by_url(project_url)
    if not project:
        logger.error(f"Project {project_url} not found")
        return {"success": False, "error": "Project not found"}
    if project.status != ProjectStatus.NEW:
        logger.error(f"Project {project_url} is not new")
        return {"success": False, "error": "Project is not new"}
    try:
        result, message = await apply_for_project(project)
        if not result:
            logger.error(f"Apply project {project_url} failed: {message}")
            return {"success": False, "error": message}
        logger.info(f"Apply project {project_url} successfully: {message}")
        return {"success": result, "message": message}
    except Exception as e:
        logger.error(f"Apply project {project_url} failed: {e}")
        return {"success": False, "error": str(e)}

@app.put("/projects/project")
async def update_project(project_url: str, project: dict[str, Any]) -> dict:
    await update_project_record(project_url, project)
    logger.info(f"Update project {project_url} successfully")
    return {"success": True}

@app.get("/projects/project")
async def get_project(project_url: str) -> dict:
    project = await get_project_by_url(project_url)
    if not project:
        return {"success": False, "error": "Project not found"}
    project_doc = project.copy()
    if "_id" in project_doc:
        project_doc["_id"] = str(project_doc["_id"])
    return {"success": True, "project": project_doc}

@app.delete("/projects/project")
async def delete_project(project_url: str) -> dict:
    project = await get_project_by_url(project_url)
    if not project:
        return {"success": False, "error": "Project not found"}
    await delete_project_record(project_url)
    logger.info(f"Delete project {project_url} successfully")
    return {"success": True}

@app.get("/projects")
async def get_projects(limit: int | None = None) -> list[dict]:
    projects = await list_projects(limit)
    return projects

@app.get("/projects/count")
async def get_projects_count() -> dict:
    count = await get_projects_count_from_repo()
    return {"success": True, "count": count}

@app.delete("/projects")
async def delete_all_projects_from_db() -> dict:
    await delete_all_projects()
    logger.info("Delete all projects successfully")
    return {"success": True}