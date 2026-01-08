from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]

def extract_projectUrl_from_emailcontent(emailcontent: str) -> str | None:
    soup = BeautifulSoup(emailcontent, "html.parser")
    body = soup.body
    if body:
        links = body.find_all("a")
        for link in links:
            if "https://www.codeur.com/projects/" in link["href"]:
                return link["href"]
    return None