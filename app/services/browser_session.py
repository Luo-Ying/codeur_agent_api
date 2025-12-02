from pathlib import Path
from typing import Optional
from playwright.async_api import Browser, BrowserContext, Page, async_playwright  # pyright: ignore[reportMissingImports]

STORAGE_STATE_PATH = Path(__file__).parent / "storage_state.json"
LOGIN_URL = "https://www.codeur.com/users/sign_in"

class CodeurBrowserSession:
    def __init__(self, storage_state_path: Path = STORAGE_STATE_PATH, headless: bool = True):
        self.storage_state_path = storage_state_path
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
    async def close(self):
        """Properly close Playwright resources: page, context, browser, and stop Playwright runner."""
        try:
            if self._page is not None:
                await self._page.close()
                self._page = None
        except Exception:
            pass
        try:
            if self._context is not None:
                await self._context.close()
                self._context = None
        except Exception:
            pass
        try:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
        except Exception:
            pass
        try:
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None
        except Exception:
            pass

    async def start(self) -> None:
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def ensure_context(self, force_fresh: bool = False) -> BrowserContext:
        await self.start()

        if self._context is not None and not force_fresh:
            return self._context

        if self._context is not None:
            await self._context.close()

        context_kwargs: dict[str, object] = {}
        if self.storage_state_path.exists() and not force_fresh:
            context_kwargs["storage_state"] = self.storage_state_path

        self._context = await self._browser.new_context(**context_kwargs)
        self._page = await self._context.new_page()
        return self._context

    async def login_once(self, force: bool = False) -> None:
        if self.storage_state_path.exists() and not force:
            return

        message = (
            "storage_state.json does not exist or is expired, please export browser cookies and run "
            "prepare_storage_state.py to generate a new state file."
        )
        raise RuntimeError(message)

    async def get_page(self) -> Page:
        if self._context is None:
            await self.ensure_context()
        assert self._page is not None
        return self._page

async def ensure_login_state(*, force: bool = False) -> None:
    session = CodeurBrowserSession()
    try:
        await session.login_once(force=force)
    finally:
        await session.close()