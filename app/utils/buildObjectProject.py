from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]

from app.services import crawler
from app.services.crawler import CodeurProjectCrawler, Crawler
from app.models.Project import Project
from app.services.globalVars import ProjectStatus

def build_object_project(email_content: str) -> tuple[Project, bool]:
    project_url = extract_projectUrl_from_emailcontent(email_content)

    codeur_project_crawler = CodeurProjectCrawler(project_url)
    if not codeur_project_crawler.check_project_availability():
        return None, False
    project_title = codeur_project_crawler.crawl_project_title()
    project_details = codeur_project_crawler.crawl_project_details()
    project_tags = codeur_project_crawler.crawl_project_tags()

    project = Project(project_title, project_details, project_tags, project_url, ProjectStatus.NEW)
    return project, True

def extract_projectUrl_from_emailcontent(emailcontent: str) -> str:
    soup = BeautifulSoup(emailcontent, "html.parser")
    body = soup.body
    if body:
        links = body.find_all("a")
        for link in links:
            if "https://www.codeur.com/projects/" in link["href"]:
                return link["href"]
    return None