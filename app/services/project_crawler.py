from typing import List
import re
import logging  
from app.services.crawler import Crawler

logger = logging.getLogger(__name__)

class CodeurProjectCrawler(Crawler):


    def __init__(self, url: str):
        super().__init__(url)
        
        self._ensure_document(url)

    def check_project_availability(self) -> bool:
        try:
            cache_key = self._cache_key(self.url) + ":availability"
            if hasattr(self, "_availability_cache") and cache_key in self._availability_cache:
                return self._availability_cache[cache_key]

            def update_cache(obj, value: bool) -> bool:
                if not hasattr(obj, "_availability_cache"):
                    obj._availability_cache = {}
                obj._availability_cache[cache_key] = value
                return value

            soup = self._ensure_document(self.url)
            if soup is None:
                return update_cache(self, False)

            container = soup.find("div", class_="flex gap-4 flex-col")
            if not container:
                return update_cache(self, False)

            p_tag = container.find("p", class_="font-medium mb-0 flex flex-wrap")
            if not p_tag:
                return update_cache(self, False)

            spans = p_tag.find_all("span", class_="whitespace-nowrap")

            for span in spans:
                text = ''.join(span.stripped_strings)

                if "ouvert" in text.lower():
                    return update_cache(self, True)

            return update_cache(self, False)
        
        except Exception as e:
            logger.error("Check project availability failed: %s", e, exc_info=True)
            if not hasattr(self, "_availability_cache"):
                self._availability_cache = {}
            self._availability_cache[cache_key] = False
            return False

    def crawl_project_title(self) -> str:
        try:
            cache_key = self._cache_key(self.url) + ":title"
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

        except Exception as e:
            logger.error("Crawl project title failed: %s", e, exc_info=True)
            self._title_cache[cache_key] = ""
            return ""

    def crawl_project_details(self) -> str:
        try:
            cache_key = self._cache_key(self.url)
            if cache_key in self._detail_cache:
                return self._detail_cache[cache_key]

            soup = self._ensure_document(self.url)
            if soup is None:
                self._detail_cache[cache_key] = ""
                return ""

            desc_div = soup.find(
                "div", 
                class_=lambda c: c and "project-description" in c
            )

            if not desc_div:
                self._detail_cache[cache_key] = ""
                return ""

            content_div = desc_div.find("div", class_="content")
            if not content_div:
                self._detail_cache[cache_key] = ""
                return ""

            text = content_div.get_text(separator="\n", strip=True)
            self._detail_cache[cache_key] = text
            return text

        except Exception as e:
            logger.error("Crawl project details failed: %s", e, exc_info=True)
            self._detail_cache[cache_key] = ""
            return ""

    def crawl_project_tags(self) -> list[str]:        
        tags = []
        try:
            cache_key = self._cache_key(self.url)
            if cache_key in self._tags_cache:
                return self._tags_cache[cache_key]

            soup = self._ensure_document(self.url)
            if soup is None:
                self._tags_cache[cache_key] = []
                return []

            p_tags = soup.find_all("p", class_="flex items-start gap-2 m-0")
            for p in p_tags:
                for span in p.find_all("span", recursive=False):
                    for node in span.descendants:
                        if getattr(node, "name", None) == "a":
                            text = node.get_text(strip=True)
                        elif not hasattr(node, "name"):
                            text = str(node).strip()
                        else:
                            continue

                        if text and text != "Profils recherchés :":
                            tags.append(text)

        except Exception as e:
            logger.error("Crawl project tags failed: %s", e, exc_info=True)
        
        self._tags_cache[cache_key] = tags
        return tags


    def crawl_project_amount(self) -> list[int]:
        try:
            cache_key = self._cache_key(self.url)
            if cache_key in self._amount_cache:
                return self._amount_cache[cache_key]

            soup = self._ensure_document(self.url)
            if soup is None:
                self._amount_cache[cache_key] = []
                return []

            def get_title(node):
                return (node.get("data-bs-original-title") 
                or node.get("title") 
                or "").strip().lower()

            tooltip_spans = soup.select('p.font-medium.mb-0.flex.flex-wrap span[data-controller="tooltip"]')
            if not tooltip_spans:
                tooltip_spans = soup.select('span[data-controller="tooltip"]')

            budget_span = next(
                (node for node in tooltip_spans if get_title(node) == "budget indicatif"),
                None
            )

            if not budget_span:
                self._amount_cache[cache_key] = []
                return []

            text = budget_span.get_text(" ", strip=True)
            raw_amounts = re.findall(r"(\d[\d\s\u00a0\u202f]*)\s*€", text)

            amounts = [
                int(re.sub(r"[^\d]", "", amt))
                for amt in raw_amounts[:2]
                if re.sub(r"[^\d]", "", amt)
            ]

            if len(amounts) == 2:
                result = amounts
            elif len(amounts) == 1:
                result = [amounts[0], amounts[0]]
            else:
                result = []

            self._amount_cache[cache_key] = result
            return result
        
        except Exception as e:
            logger.error("Crawl project amount failed: %s", e, exc_info=True)
            self._amount_cache[cache_key] = []
            return []