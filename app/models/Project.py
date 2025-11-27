from app.models import Client
from app.services.globalVars import project_status

class Project:
    def __init__(self, title: str, description: str, tags: list[str], url: str, client: Client, status: project_status):
        self.title = title
        self.description = description
        self.tags = tags
        self.url = url 
        self.client = client
        self.status = status

    def __str__(self):
        return f"Project(title={self.title}, description={self.description}, tags={self.tags}, url={self.url}, client={self.client}, status={self.status})"