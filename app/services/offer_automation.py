import asyncio
from requests import Response
from app.models import OfferPayload
from app.services import CodeurBrowserSession
from playwright.async_api import Page  # pyright: ignore[reportMissingImports]
import logging

from app.services.logging import setup_logging

logger = logging.getLogger(__name__)

class CodeurOfferAutomation:
    def __init__(self, session: CodeurBrowserSession):
        self.session = session
        self._page: Page | None = None

    async def _ensure_page(self) -> Page:
        if self._page is None:
            await self.session.ensure_context()
            self._page = await self.session.get_page()
        return self._page

    async def open_offer_form(self, payload: OfferPayload) -> None:
        page = await self._ensure_page()
        await page.goto(payload.project_url, wait_until="networkidle")
        await page.click('a:text("Faire une offre")')
        # wait for the form fields to appear (stronger guarantee)
        await page.wait_for_selector("#offer_amount", timeout=20000)
        await page.wait_for_selector("#offer_pricing_mode", state="attached")
        await page.wait_for_selector("#offer_duration", timeout=20000)
        await page.wait_for_selector("#offer_comments_attributes_0_content", timeout=20000)
        await page.wait_for_selector('input#offer_level_standard', state="attached")
        await page.wait_for_selector('input#offer_level_super', state="attached")

    async def fill_offer_form(self, payload: OfferPayload) -> None:
        page = await self._ensure_page()
        await page.locator(f'label[for="offer_level_{payload.level}"]').click()

        await page.fill("#offer_amount", str(payload.amount))
        await page.evaluate(
            """(value) => {
                const select = document.querySelector('#offer_pricing_mode');
                const dropdown = select?.closest('.ui.dropdown');
                if (!select) throw new Error('pricing mode select missing');
                select.value = value;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                dropdown?.setAttribute('data-value', value);
            }""",
            payload.pricing_mode,
        )
        await page.fill("#offer_duration", str(payload.duration))
        await page.fill("#offer_comments_attributes_0_content", payload.message)

        # important: trigger input event, otherwise the button will not be unlocked
        await page.dispatch_event("#offer_comments_attributes_0_content", "input")

    async def submit_offer(self) -> None:
        page = await self._ensure_page()

        await page.wait_for_function(
            """() => {
            const btn = document.querySelector('input[data-offer-form-target="submit"]');
            return btn && !btn.disabled;
            }""",
            timeout=15000
        )

        async with page.expect_response(
            lambda response: (
                "offers" in response.url and response.request.method == "POST"
            )
        ) as response_info:
            await page.click('input[data-offer-form-target="submit"]')

        response = await response_info.value

        if response.status in (200, 201, 204, 302):
            logger.info("Received successful /offers response (2xx/302).")
            return True

        # if 4xx/422, log the response body
        if 400 <= response.status < 500:
            try:
                text = await response.text()
                logger.warning(f"Offer submit failed, status: {response.status}, body: {text}")
            except Exception as exc:
                logger.warning(f"Offer submit failed, status: {response.status}, "
                               f"and unable to get body due to: {exc}")
        return False

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

async def apply_once(payload: OfferPayload, *, headless: bool = True) -> tuple[bool, str]:
    session = CodeurBrowserSession(headless=headless)
    automation = CodeurOfferAutomation(session)
    try:
        result = await automation.apply(payload)
        if not result:
            return False, f"Failed to apply for project {payload.project_url}"
        else:
            return True, f"Applied for project {payload.project_url} successfully"
    except Exception as e:
        logger.error(f"Failed to apply for project: {e}")
        return False, f"Failed to apply for project {payload.project_url}: {e}"
    finally:
        await session.close()