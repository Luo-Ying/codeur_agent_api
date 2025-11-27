import datetime
import imaplib
import logging


class MailConnectionConfig:
    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl

class MailConnection:
    def __init__(self, config: MailConnectionConfig):
        self.config = config
        self.connection = None

    def connect(self):
        if self.config.use_ssl:
            self.connection = imaplib.IMAP4_SSL(self.config.host, self.config.port)
            self.connection.login(self.config.username, self.config.password)
        else:
            self.connection = imaplib.IMAP4(self.config.host, self.config.port)
            self.connection.login(self.config.username, self.config.password)

    def disconnect(self):
        if self.connection:
            self.connection.logout()
            self.connection = None


class MailBox:
    def __init__(self, connection: MailConnection, debug: bool = False):
        self.mail_connection = connection
        self.debug = debug

    def open(self):
        self.mail_connection.connect()

    def getListUnreadEmails(self):
        # Select INBOX
        status, _ = self.mail_connection.connection.select("INBOX")
        if status != "OK":
            if self.debug:
                logging.debug("IMAP select inbox failed: %s", status)
            return []

        # Only search for unseen emails
        status, data = self.mail_connection.connection.search(None, 'UNSEEN')
        if self.debug:
            logging.debug("IMAP search status: %s", status)
            logging.debug("Raw UNSEEN payload: %s", data)

        if status != "OK" or not data:
            if self.debug:
                logging.debug("Search for UNSEEN emails returned nothing or failed.")
            return []

        # Split email IDs
        email_ids = data[0].split() if data[0] else []

        # Debug: Print flags for each email
        if self.debug:
            for raw_id in email_ids:
                flag_status, flag_data = self.mail_connection.connection.fetch(raw_id, "(FLAGS)")
                logging.debug(
                    "Email %s flags: status=%s data=%s",
                    raw_id.decode() if isinstance(raw_id, bytes) else raw_id,
                    flag_status,
                    flag_data,
                )

        # Convert to string IDs
        return [
            raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            for raw_id in email_ids
        ]




    def getEmail(self, email_id: str):
        message_id = email_id.decode().strip() if isinstance(email_id, bytes) else str(email_id).strip()

        if self.debug:
            flag_status, flag_data = self.mail_connection.connection.fetch(message_id, "(FLAGS)")
            logging.debug("Pre-fetch flags for %s: status=%s data=%s", message_id, flag_status, flag_data)

        status, email_data = self.mail_connection.connection.fetch(message_id, "(BODY.PEEK[])")
        if status == "OK":
            return email_data
        else:
            return None

    def close(self):
        self.mail_connection.disconnect()


import email
from email.header import decode_header

class Email:
    def __init__(self, email):
        self.email = email
        self.email_title = ""
        self.email_from = ""
        self.email_content = ""

    def decode_header_value(self, header_value):
        """decode any email header field to a readable string"""
        if not header_value:
            return ""
        parts = decode_header(header_value)
        decoded = ""
        for text, charset in parts:
            if isinstance(text, bytes):
                decoded += text.decode(charset or "utf-8", errors="ignore")
            else:
                decoded += text
        return decoded

    def parse_email(self):
        """
        raw_tuple like:
        (b'49 (RFC822 {7854}', b'.....email content.....')
        """
        raw_email = self.email[0][1]

        # email headers
        msg = email.message_from_bytes(raw_email)
        self.email_title = self.decode_header_value(msg.get("Subject")) 
        self.email_from = self.decode_header_value(msg.get("From"))

        # email content
        self.email_content = self.get_email_content_text(msg)
        return self.email_title, self.email_from, self.email_content

    def get_email_content_text(self, msg: email.message.Message) -> str:
        email_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    email_content = part.get_payload(decode=True).decode(charset, errors="ignore")
                    break
        else:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True).decode(charset, errors="ignore")
            email_content = payload
        return email_content