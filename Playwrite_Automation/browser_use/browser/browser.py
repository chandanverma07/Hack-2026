from playwright.async_api import async_playwright

class BrowserConfig:
    def __init__(self, headless=True, extra_chromium_args=None):
        self.headless = headless
        self.extra_chromium_args = extra_chromium_args or []

class Browser:
    def __init__(self, config: BrowserConfig):
        self.config = config
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def launch(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            args=self.config.extra_chromium_args
        )
        self.context = await self.browser.new_context(accept_downloads=True)
        self.page = await self.context.new_page()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
