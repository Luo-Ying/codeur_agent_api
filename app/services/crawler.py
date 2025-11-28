import random
import time
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import requests
import urllib.robotparser as robotparser
from bs4 import BeautifulSoup

class Crawler:
    USER_AGENT = "CodeurAgentCrawler/1.0 (yingqi.luo.fr@gmail.com)"
    REQUEST_TIMEOUT = 5
    REQUEST_DELAY_RANGE = (1.0, 5.0)
    MAX_RETRIES = 3
    BACKOFF_BASE = 2

    _robots_cache: Dict[Tuple[str, str, str], Optional[robotparser.RobotFileParser]] = {}

    def __init__(
        self,
        url: str,
        session: Optional[requests.Session] = None,
        user_agent: Optional[str] = None,
    ):
        self.url = self._request_without_params(url)
        self.user_agent = user_agent or self.USER_AGENT
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.7",
                "Connection": "keep-alive",
            }
        )
        self._page_cache: Dict[str, str] = {}

    def crawl_project_details(self) -> str:
        print("crawling project details: ", self.url)
        if not self._is_allowed(self.url):
            return ""

        if self.url in self._page_cache:
            return self._page_cache[self.url]

        html = self._request_with_retries(self.url)
        soup = BeautifulSoup(html, "html.parser")

        desc_div = soup.find("div", class_="project-description break-words")
        if not desc_div:
            self._page_cache[self.url] = ""
            return ""

        content_div = desc_div.find("div", class_="content")
        if content_div:
            text = content_div.get_text(separator="\n", strip=True)
            self._page_cache[self.url] = text
            return text

        text = desc_div.get_text(separator="\n", strip=True)
        self._page_cache[self.url] = text
        return text

    def _request_without_params(self, url: str) -> str:
        # Remove everything from the first '?' (including '?') in the URL
        idx = url.find("?")
        if idx != -1:
            url = url[:idx]
        return url

    def _request_with_retries(self, url: str) -> str:
        retries = 0
        backoff = 1.0
        while retries < self.MAX_RETRIES:
            try:
                response = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                retries += 1
                self._courtesy_delay()
                if retries >= self.MAX_RETRIES:
                    raise exc
                self._backoff_sleep(backoff)
                backoff *= self.BACKOFF_BASE
                continue

            try:
                if response.status_code in (429, 503):
                    retries += 1
                    if retries >= self.MAX_RETRIES:
                        response.raise_for_status()
                    self._backoff_sleep(backoff)
                    backoff *= self.BACKOFF_BASE
                    continue
                response.raise_for_status()
                return response.text
            finally:
                self._courtesy_delay()

        raise requests.HTTPError(f"Unable to fetch {url} after {self.MAX_RETRIES} retries.")

    # delay for 1-5 seconds
    def _courtesy_delay(self) -> None:
        time.sleep(random.uniform(*self.REQUEST_DELAY_RANGE))

    # delay for 1-2 seconds
    def _backoff_sleep(self, backoff: float) -> None:
        time.sleep(backoff + random.uniform(0, 1))

    # check if the url complies with the site policy
    def _is_allowed(self, target_url: str) -> bool:
        parser = self._ensure_robot_parser(target_url)
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, target_url)

    # ensure the robot parser is cached and return the robot parser
    def _ensure_robot_parser(self, target_url: str) -> Optional[robotparser.RobotFileParser]:
        parsed = urlparse(target_url)
        key = (parsed.scheme, parsed.netloc, self.user_agent)
        if key in self._robots_cache:
            return self._robots_cache[key]

        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        parser: Optional[robotparser.RobotFileParser] = robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = self.session.get(robots_url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            parser.parse(response.text.splitlines())
        except requests.RequestException:
            parser = None
        finally:
            self._courtesy_delay()

        self._robots_cache[key] = parser
        return parser