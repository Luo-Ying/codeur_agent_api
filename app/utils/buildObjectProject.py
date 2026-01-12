import logging

from app.services import CodeurProjectCrawler
from app.models.Project import Project
from app.services.globalVars import ProjectStatus
from app.utils.someCommonFunctions import extract_projectUrl_from_emailcontent
from app.services.logging import setup_logging

logger = logging.getLogger(__name__)

def build_object_project(email_content: str) -> tuple[Project | None, bool]:
    project_url = extract_projectUrl_from_emailcontent(email_content)
    if project_url is None:
        return None, False
    crawler = CodeurProjectCrawler(project_url)
    if not crawler.check_project_availability():
        return None, False
    project_title = crawler.crawl_project_title()
    project_details = crawler.crawl_project_details()
    project_tags = crawler.crawl_project_tags()
    project_amount = crawler.crawl_project_amount() if crawler.crawl_project_amount() is not None else [1000, 1000]
    project = Project(project_title, project_details, project_tags, project_url, project_amount, ProjectStatus.NEW)
    return project, True