from app.services.crawler import Crawler

class CodeurProjectCrawler(Crawler):
    def __init__(self, url: str):
        super().__init__(url)
        self._availability_cache: dict[str, bool] = {}
        self._amount_cache: dict[str, list[int] | int] = {}
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

    def crawl_project_amount(self) -> int:
        cache_key = self._cache_key(self.url)
        if cache_key in self._amount_cache:
            return self._amount_cache[cache_key]

        soup = self._ensure_document(self.url)
        if soup is None:
            self._amount_cache[cache_key] = 0
            return 0

        # Find the <p> element containing budget info
        budget_p = soup.find("p", class_="font-medium mb-0 flex flex-wrap")
        if not budget_p:
            self._amount_cache[cache_key] = 0
            return 0

        # Find <span> with data-controller="tooltip" and data-bs-original-title="Budget indicatif"
        budget_span = budget_p.find("span", {"data-controller": "tooltip", "data-bs-original-title": "Budget indicatif"})
        if not budget_span:
            self._amount_cache[cache_key] = 0
            return 0

        text = budget_span.get_text(strip=True)
        # Example expected: "500 € à 1 000 €"
        import re
        # Find numbers (may contain thousands separators or non-breaking spaces)
        result = re.findall(r"(\d[\d\s\u00a0]*)\s*€", text)
        if len(result) >= 2:
            min_amount = int(result[0].replace(" ", "").replace(" ", ""))
            max_amount = int(result[1].replace(" ", "").replace(" ", ""))
            self._amount_cache[cache_key] = [min_amount, max_amount]
            return [min_amount, max_amount]
        elif len(result) == 1:
            amount = int(result[0].replace(" ", "").replace(" ", ""))
            self._amount_cache[cache_key] = [amount, amount]
            return [amount, amount]

        self._amount_cache[cache_key] = 0
        return 0