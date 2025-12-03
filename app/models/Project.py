from app.services.globalVars import ProjectStatus

class Project:
    def __init__(self, title: str, description: str, tags: list[str], url: str, amount: list[int], status: ProjectStatus | str):
        self.title = title
        self.description = description
        self.tags = tags
        self.url = url
        self.amount = amount
        self.status = status.value if isinstance(status, ProjectStatus) else status # type: ignore

    def __str__(self) -> str:
        return f"Project(title={self.title}, description={self.description}, tags={self.tags}, url={self.url}, amount={self.amount}, status={self.status})"