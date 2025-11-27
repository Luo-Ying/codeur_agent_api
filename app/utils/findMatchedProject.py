from app.models import Project
from bs4 import BeautifulSoup

def is_matched_project(emailcontent: str) -> bool:
    emailcontent = extract_text_from_html(emailcontent)
    print("emailcontent: ", emailcontent)
    return None

def extract_text_from_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    # Try to extract from common tags
    body = soup.body
    if body:
        return body.get_text(separator='\n', strip=True)
    # fallback: get all text
    return soup.get_text(separator='\n', strip=True)