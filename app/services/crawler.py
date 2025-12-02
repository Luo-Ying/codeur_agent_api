from typing import Dict, Optional, Tuple
import requests
import urllib.robotparser as robotparser
from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]
from urllib.parse import urlparse, urljoin, parse_qs, urlencode
import time
import random


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
        self.url = url
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
        self._soup_cache: Dict[str, BeautifulSoup] = {}
        self._detail_cache: Dict[str, str] = {}
        self._title_cache: Dict[str, str] = {}
        self._tags_cache: Dict[str, list[str]] = {}
        self._client_url_cache: Dict[str, str] = {}
        self.html: Optional[str] = None
        self.soup: Optional[BeautifulSoup] = None

    def _ensure_document(self, url: str) -> Optional[BeautifulSoup]:
        cache_key = self._cache_key(url)
        if cache_key in self._soup_cache:
            self.html = self._page_cache.get(cache_key)
            self.soup = self._soup_cache[cache_key]
            return self.soup

        html = self._fetch_html(url)
        if html is None:
            self.html = None
            self.soup = None
            return None

        soup = BeautifulSoup(html, "html.parser")
        self._page_cache[cache_key] = html
        self._soup_cache[cache_key] = soup
        self.html = html
        self.soup = soup
        return soup

    def _fetch_html(self, url: str) -> Optional[str]:
        if not self._complies_with_site_policy(url):
            return None

        cache_key = self._cache_key(url)
        if cache_key in self._page_cache:
            return self._page_cache[cache_key]

        if not self._can_fetch(cache_key):
            return None

        html = self._request_with_retries(cache_key)
        if html is not None:
            self._page_cache[cache_key] = html
        return html

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = [
            ("page", value)
            for key, values in params.items()
            if key == "page"
            for value in values
        ]
        normalized_query = urlencode(filtered_params)
        normalized = parsed._replace(query=normalized_query)
        return normalized.geturl()

    def _cache_key(self, url: Optional[str] = None) -> str:
        reference_url = url or self.url
        return self._normalize_url(reference_url)

    def _request_with_retries(self, url: str) -> Optional[str]:
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

    def _courtesy_delay(self) -> None:
        time.sleep(random.uniform(*self.REQUEST_DELAY_RANGE))

    def _backoff_sleep(self, backoff: float) -> None:
        time.sleep(backoff + random.uniform(0, 1))

    def _complies_with_site_policy(self, target_url: str) -> bool:
        parsed = urlparse(target_url)
        if parsed.path.startswith("/system/projects/"):
            return False

        params = parse_qs(parsed.query, keep_blank_values=True)
        disallowed_params = set(params.keys()) - {"page"}
        return not disallowed_params

    def _can_fetch(self, target_url: str) -> bool:
        parser = self._ensure_robot_parser(target_url)
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, target_url)

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