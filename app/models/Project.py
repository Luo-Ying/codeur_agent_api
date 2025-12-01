from app.services.globalVars import ProjectStatus

class Project:
    def __init__(self, title: str, description: str, tags: list[str], url: str, status: ProjectStatus | str):
        self.title = title
        self.description = description
        self.tags = tags
        self.url = url
        self.status = status.value if isinstance(status, ProjectStatus) else status

    def __str__(self):
        return f"Project(title={self.title}, description={self.description}, tags={self.tags}, url={self.url}, status={self.status})"