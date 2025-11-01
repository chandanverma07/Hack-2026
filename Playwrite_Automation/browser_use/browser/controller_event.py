import os
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class Controller:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password

    async def execute(self, task, browser) -> str:
        page: Page = browser.page
        screenshot_dir = os.path.join(os.getcwd(), "local_screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, "event_creation_success.png")

        try:
            logger.info("Navigating to login page...")
            await page.goto(self.base_url)
            await page.wait_for_selector("text=Sign In")

            logger.info("Logging in...")
            await page.get_by_role("textbox", name="Email").fill(self.username)
            await page.get_by_role("textbox", name="Password").fill(self.password)
            await page.get_by_role("button", name="Sign In").click()
            await page.wait_for_load_state("networkidle")

            logger.info("Login successful.")
            await page.get_by_role("link", name="Create Event").click()
            await page.wait_for_selector("text=Event Title *")

            logger.info("Filling event details...")
            await page.get_by_role("textbox", name="Event Title *").fill(
                "GreenEdge Expo – Driving Sustainable Innovation"
            )
            await page.get_by_role("textbox", name="Description").fill(
                "An event dedicated to sustainability and green technology, featuring eco-tech startups, environmental policy discussions, and workshops."
            )
            await page.get_by_role("textbox", name="Location").fill("INDIA")

            await page.get_by_role("textbox", name="Start Date & Time *").fill("2025-11-01T22:00")
            await page.get_by_role("textbox", name="End Date & Time *").fill("2025-11-01T23:00")

            logger.info("Submitting the form...")
            await page.get_by_role("button", name="Create Event").click()
            await page.wait_for_timeout(3000)

            if await page.is_visible("button:has-text('Generate Agenda with AI')"):
                logger.info("Clicking Generate Agenda with AI...")
                await page.get_by_role("button", name="Generate Agenda with AI").click()
                await page.wait_for_timeout(2000)

            await page.screenshot(path=screenshot_path)
            logger.info(f"Event created successfully. Screenshot saved at {screenshot_path}")
            return screenshot_path

        except Exception as e:
            logger.exception("Event automation failed.")
            await page.screenshot(path="event_error.png")
            return ""
