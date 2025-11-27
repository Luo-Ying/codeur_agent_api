import datetime

class Statistics:
    def __init__(self, published_projects: int, finished_projects: int, late_connections: datetime, member_since: datetime):
        self.published_projects = published_projects
        self.finished_projects = finished_projects
        self.late_connections = late_connections
        self.member_since = member_since

    def __str__(self):
        return f"Statistics(published_projects={self.published_projects}, finished_projects={self.finished_projects}, late_connections={self.late_connections}, member_since={self.member_since})"