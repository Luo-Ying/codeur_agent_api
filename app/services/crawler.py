import random
import time
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
import urllib.robotparser as robotparser
from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]


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


class CodeurProjectCrawler(Crawler):
    def __init__(self, url: str):
        super().__init__(url)
        self._ensure_document(url)

    def check_project_availability(self) -> bool:
        cache_key = self._cache_key(self.url) + ":availability"
        if hasattr(self, "_availability_cache") and cache_key in self._availability_cache:
            return self._availability_cache[cache_key]

        soup = self._ensure_document(self.url)
        if soup is None:
            if not hasattr(self, "_availability_cache"):
                self._availability_cache = {}
            self._availability_cache[cache_key] = False
            return False

        container = soup.find("div", class_="flex gap-4 flex-col")
        if not container:
            if not hasattr(self, "_availability_cache"):
                self._availability_cache = {}
            self._availability_cache[cache_key] = False
            return False

        p_tag = container.find("p", class_="font-medium mb-0 flex flex-wrap")
        if not p_tag:
            if not hasattr(self, "_availability_cache"):
                self._availability_cache = {}
            self._availability_cache[cache_key] = False
            return False

        # The <span> for "Ouvert" contains a <svg>, then '&nbsp;', then text "Ouvert"
        for span in p_tag.find_all("span", class_="whitespace-nowrap"):
            # Clean the text, Chrome/BeautifulSoup may interpret &nbsp; as u"\xa0"
            text = ''.join(span.stripped_strings)
            if "Ouvert" in text:
                if not hasattr(self, "_availability_cache"):
                    self._availability_cache = {}
                self._availability_cache[cache_key] = True
                return True

        if not hasattr(self, "_availability_cache"):
            self._availability_cache = {}
        self._availability_cache[cache_key] = False
        return False

    def crawl_project_title(self) -> str:
        cache_key = self._cache_key(self.url)
        if cache_key in self._title_cache:
            return self._title_cache[cache_key]

        soup = self._ensure_document(self.url)
        if soup is None:
            self._title_cache[cache_key] = ""
            return ""

        h1_tag = soup.find("h1", class_="text-3xl lg:text-4xl font-bold mb-4 text-darker")
        if h1_tag:
            text = h1_tag.get_text(strip=True)
            self._title_cache[cache_key] = text
            return text

        self._title_cache[cache_key] = ""
        return ""

    def crawl_project_details(self) -> str:
        cache_key = self._cache_key(self.url)
        if cache_key in self._detail_cache:
            return self._detail_cache[cache_key]

        soup = self._ensure_document(self.url)
        if soup is None:
            self._detail_cache[cache_key] = ""
            return ""

        desc_div = soup.find("div", class_="project-description break-words")
        if not desc_div:
            self._detail_cache[cache_key] = ""
            return ""

        content_div = desc_div.find("div", class_="content")
        if content_div:
            text = content_div.get_text(separator="\n", strip=True)
            self._detail_cache[cache_key] = text
            return text

        self._detail_cache[cache_key] = ""
        return ""

    def crawl_project_tags(self) -> list[str]:
        cache_key = self._cache_key(self.url)
        if cache_key in self._tags_cache:
            return self._tags_cache[cache_key]

        soup = self._ensure_document(self.url)
        if soup is None:
            self._tags_cache[cache_key] = []
            return []

        tags = []
        p_tags = soup.find_all("p", class_="flex items-start gap-2 m-0")
        for p in p_tags:
            # Find all <span> under <p>
            spans = p.find_all("span", recursive=False)
            for span in spans:
                # If there are inner <span>, skip the SVG icon span and only process text/links
                # Get all descendants that are NavigableString or <a>
                for descendant in span.descendants:
                    if getattr(descendant, "name", None) == "a":
                        text = descendant.get_text(strip=True)
                        if text:
                            tags.append(text)
                    elif not hasattr(descendant, "name"):
                        text = str(descendant).strip()
                        if text and text != "Profils recherchés :":
                            tags.append(text)
        self._tags_cache[cache_key] = tags
        return tags