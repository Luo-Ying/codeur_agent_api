from fastapi import FastAPI # pyright: ignore[reportMissingImports]
import os
from dotenv import load_dotenv

from app.services.mailBox import Email, MailBox, MailConnection, MailConnectionConfig
from app.utils.findMatchedProject import is_matched_project
from app.utils.buildObjectProject import build_object_project

app = FastAPI()

load_dotenv()
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.get("/get_codeur_new_project_matched")
def get_codeur_new_project_matched() -> list[dict]:
    mail_box = MailBox(MailConnection(MailConnectionConfig(
        host="imap.gmail.com", 
        port=993, 
        username=EMAIL_USERNAME, 
        password=EMAIL_PASSWORD
    )))
    mail_box.open()
    unread_emails = mail_box.getListUnreadEmails()
    project_list = []

    # filter emails by email_from and email_title and is_matched_project
    for email_id in unread_emails:
        email = mail_box.getEmail(email_id)
        email_obj = Email(email)
        email_title, email_from, email_content = email_obj.parse_email()
        if "notification@compte.codeur.com" not in email_from or "Nouveau projet" not in email_title:
            continue
        if not is_matched_project(email_content):
            continue
        project, is_project_available = build_object_project(email_content)
        if is_project_available and project is not None:
            project_list.append(project.__dict__)
    
    # email = mail_box.getEmail(unread_emails[500])
    # email_obj = Email(email)
    # email_title, email_from, email_content = email_obj.parse_email()
    # is_matched = is_matched_project(email_content)
    # # print("email content: ", email_content, "\n")
    # print("email from: ", email_from, "\n")
    # print("email title: ", email_title, "\n")
    # print("is matched project: ", is_matched, "\n")
    # project, is_project_available = build_object_project(email_content)
    # print("project: ", project, "\n")
    # print("is project available: ", is_project_available, "\n")

    # print("project list: ", project_list, "\n")

    mail_box.close()
    return project_list


# TODO: apply project
# @app.post("/apply_project")
# def apply_project(project_id: str):
    