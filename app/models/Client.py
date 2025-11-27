from app.models.Statistics import Statistics


class Client:
    def __init__(self, username: str, location: str, about: str, statistics: Statistics):
        self.username = username
        self.location = location
        self.about = about
        self.statistics = statistics

    def __str__(self):
        return f"Client(username={self.username}, location={self.location}, about={self.about}, statistics={self.statistics})"