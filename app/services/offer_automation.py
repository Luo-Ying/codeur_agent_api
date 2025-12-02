import asyncio
from requests import Response
from app.models import OfferPayload
from app.services import CodeurBrowserSession
from playwright.async_api import Page  # pyright: ignore[reportMissingImports]


class CodeurOfferAutomation:
    def __init__(self, session: CodeurBrowserSession):
        self.session = session
        self._page: Page | None = None

    async def _ensure_page(self) -> Page:
        if self._page is None:
            await self._session.ensure_context()
            self._page = await self._session.get_page()
        return self._page

    async def open_offer_form(self, payload: OfferPayload) -> None:
        page = await self._ensure_page()
        await page.goto(payload.project_url, wait_until="networkidle")
        await page.click('a:text("Faire une offre")')
        # wait for the form fields to appear (stronger guarantee)
        await page.wait_for_selector("#offer_amount", timeout=20000)
        await page.wait_for_selector("#offer_pricing_mode", timeout=20000)
        await page.wait_for_selector("#offer_duration", timeout=20000)
        await page.wait_for_selector("#offer_comments_attributes_0_content", timeout=20000)
        await page.wait_for_selector('input#offer_level_standard', timeout=20000)
        await page.wait_for_selector('input#offer_level_super', timeout=20000)

    async def fill_offer_form(self, payload: OfferPayload) -> None:
        page = await self._ensure_page()
        level_selector = "#offer_level_standard" if payload.level == "standard" else "#offer_level_super"
        await page.check(level_selector)
        await page.wait_for_load_state("networkidle")
        await page.fill("#offer_amount", str(payload.amount))
        await page.wait_for_load_state("networkidle")
        await page.select_option("#offer_pricing_mode", payload.pricing_mode)
        await page.wait_for_load_state("networkidle")
        await page.fill("#offer_duration", str(payload.duration))
        await page.wait_for_load_state("networkidle")
        await page.fill("#offer_comments_attributes_0_content", payload.message)
        await page.wait_for_load_state("networkidle")

    async def submit_offer(self) -> None:
        page = await self._ensure_page()
        await asyncio.gather(
            self._wait_offer_submit_response(page),
            page.click('input[type="submit"][value="Publier mon offre"]')
        )
        try:
            await page.wait_for_selector('#project-actions .text-warning:has-text("Offre déposée")', timeout=30000)
            return True
        except TimeoutError:
            raise RuntimeError("Failed to submit offer, please check the form and try again")

    async def _wait_offer_submit_response(self, page: Page) -> bool:
        def is_offer_submit(response: Response) -> bool:
            return response.request.method == "POST" and "/offers" in response.request.url and response.status < 400
        response = await page.wait_for_response(is_offer_submit, timeout=30000)
        if response is None:
            raise RuntimeError("Failed to submit offer")
        return True

    async def apply(self, payload: OfferPayload) -> bool:
        try:
            await self.open_offer_form(payload)
            await self.fill_offer_form(payload)
            return await self.submit_offer()
        except Exception as e:
            raise RuntimeError(f"Failed to apply for project: {e}")

async def apply_once(payload: OfferPayload, *, headless: bool = True) -> None:
    session = CodeurBrowserSession(headless=headless)
    automation = CodeurOfferAutomation(session)
    try:
        await automation.apply(payload)
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to apply for project: {e}")
    finally:
        await session.close()