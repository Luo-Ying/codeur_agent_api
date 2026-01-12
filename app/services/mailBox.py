import imaplib
import logging

from app.services.logging import setup_logging

logger = logging.getLogger(__name__)

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
                logger.debug(f"IMAP select inbox failed: {status}")
            return []

        # Only search for unseen emails
        status, data = self.mail_connection.connection.uid(
            "SEARCH",
            None, 
            'X-GM-RAW "in:inbox is:unread"'
        )

        if self.debug:
            logger.debug(f"IMAP search status: {status}")
            logger.debug(f"Raw UNSEEN payload: {data}")

        if status != "OK" or not data:
            if self.debug:
                logger.debug("Search for UNSEEN emails returned nothing or failed.")
            return []

        # Split email IDs
        email_ids = data[0].split() if data[0] else []

        # Debug: log the flags for each email
        if self.debug:
            for raw_uid in email_ids:
                flag_status, flag_data = self.mail_connection.connection.uid(
                    "FETCH", raw_uid, "(FLAGS)"
                )
                logger.debug(
                    f"Email UID {raw_uid.decode()} flags: {flag_status} {flag_data}",
                )

        # Convert to string IDs
        return [
            raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            for raw_id in email_ids
        ]

    def getEmail(self, email_id: str):
        message_uid = email_id.decode().strip() if isinstance(email_id, bytes) else str(email_id).strip()

        if not message_uid:
            if self.debug:
                logger.debug("Empty email identifier received while fetching email.")
            return None

        if self.debug:
            flag_status, flag_data = self.mail_connection.connection.uid("FETCH", message_uid, "(FLAGS)")
            logger.debug(f"Pre-fetch flags for {message_uid}: status={flag_status} data={flag_data}")

        status, email_data = self.mail_connection.connection.uid("FETCH", message_uid, "(BODY.PEEK[])")
        if status != "OK" or not email_data:
            if self.debug:
                logger.debug(f"Failed to fetch email UID {message_uid}: status={status} data={email_data}")
            return None

        # filter out None placeholders that some IMAP servers return
        return [chunk for chunk in email_data if chunk]
    
    def moveEmailToLabel(self, email_id: str, label: str) -> bool:
        """
        Move the specified email to the specified label.
        Returns True if the operation was successful, False otherwise.
        """
        try:
            conn = self.mail_connection.connection
            
            status, _ = conn.select("INBOX")
            if status != "OK":
                return False
            
            status, _ = conn.uid(
                "STORE", 
                email_id,
                "+X-GM-LABELS",
                f"({label})"    
            )
            if status != "OK":
                return False
            
            status, _ = conn.uid(
                "STORE",
                email_id,
                "+FLAGS",
                "(\\Deleted)"
            )
            if status != "OK":
                return False
            
            conn.expunge()
            return True
        
        except Exception as e:
            if self.debug:
                logger.debug(f"Exception moving email to label: {e}")
            return False

    def setEmailSeen(self, email_uid: str) -> bool:
        """
        Attempts to mark the specified email as read (seen). 
        Returns True if the operation was successful, False otherwise.
        """
        try:
            # must be in read-write mode
            status, _ = self.mail_connection.connection.select("INBOX", readonly=False)
            if status != "OK":
                return False

            # Use UID STORE instead of STORE
            status, response = self.mail_connection.connection.uid(
                "STORE",
                email_uid,
                "+FLAGS",
                "\\Seen"
            )

        except Exception as e:
            if self.debug:
                logger.debug(f"Exception marking email seen: {e}")
            return False

        return status == "OK"
    
    def deleteEmailFromInbox(self, email_uid: str) -> bool:
        """
        Delete the specified email from the inbox.
        Returns True if the operation was successful, False otherwise.
        """
        try:
            conn = self.mail_connection.connection
            status, _ = conn.select("INBOX")
            if status != "OK":
                return False

            status, _ = conn.uid(
                "STORE",
                email_uid,
                "+FLAGS",
                "(\\Deleted)"
            )
            if status != "OK":
                return False

            conn.expunge()
            return True

        except Exception as e:
            if self.debug:
                logger.debug(f"Exception deleting email from inbox: {e}")
            return False
        
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

    def _extract_raw_email_bytes(self):
        """
        Extract the raw email payload bytes from the IMAP response.
        Returns None if no payload was found.
        """

        def extract(entry):
            if entry is None:
                return None

            if isinstance(entry, tuple):
                if len(entry) >= 2 and isinstance(entry[1], (bytes, bytearray)):
                    return bytes(entry[1])
                # fall back to inspecting individual parts
                for sub_entry in entry:
                    candidate = extract(sub_entry)
                    if candidate is not None:
                        return candidate
                return None

            if isinstance(entry, list):
                for sub_entry in entry:
                    candidate = extract(sub_entry)
                    if candidate is not None:
                        return candidate
                return None

            if isinstance(entry, (bytes, bytearray)):
                stripped = entry.strip()
                if not stripped or stripped == b")":
                    return None
                first_token = stripped.split(b" ", 1)[0]
                if first_token.isdigit():
                    # metadata such as "49 (BODY..." should be ignored
                    return None
                return bytes(entry)

            return None

        return extract(self.email)

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
        parse the email and return the email title, email from, email content.....
        
        raw_tuple like:
        (b'49 (RFC822 {7854}', b'.....email content.....')
        """
        raw_email = self._extract_raw_email_bytes()
        if raw_email is None:
            raise ValueError("IMAP response missing raw email payload")

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
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        email_content = payload.decode(charset, errors="ignore")
                    elif isinstance(payload, str):
                        email_content = payload
                    break
        else:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                email_content = payload.decode(charset, errors="ignore")
            elif isinstance(payload, str):
                email_content = payload
        return email_content