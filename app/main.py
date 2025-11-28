from fastapi import FastAPI, Query, UploadFile, File  # pyright: ignore[reportMissingImports]
import shutil
import os
from dotenv import load_dotenv
import email
from email.header import decode_header

from app.services.mailBox import Email, MailBox, MailConnection, MailConnectionConfig
from app.utils.findMatchedProject import is_matched_project
from app.services import globalVars

app = FastAPI()

load_dotenv()
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.get("/get_codeur_new_project_matched")
def get_codeur_new_project_matched():    
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
    # for email_id in unread_emails:
    #     email = mail_box.getEmail(email_id)
    #     email_obj = Email(email)
    #     email_title, email_from, email_content = email_obj.parse_email()
    #     if "notification@compte.codeur.com" not in email_from or "Nouveau projet" not in email_title:
    #         continue
    #     if not is_matched_project(email_content):
    #         continue
    #     # TODO: get matched project details and convert to project object


        # project = convert_emailcontent_to_project(email_content)
        # project_list.append(project)
    
    email = mail_box.getEmail(unread_emails[500])
    email_obj = Email(email)
    email_title, email_from, email_content = email_obj.parse_email()
    # print("email content: ", email_content, "\n")
    print("email from: ", email_from, "\n")
    print("email title: ", email_title, "\n")
    print("is matched project: ", is_matched_project(email_content), "\n")


    # print("project list: ", project_list, "\n")


    mail_box.close()
    return project_list