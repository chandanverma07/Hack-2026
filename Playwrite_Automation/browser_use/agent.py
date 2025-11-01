import logging

logger = logging.getLogger(__name__)

class Agent:
    def __init__(self, task, llm, controller, browser):
        self.task = task
        self.llm = llm
        self.controller = controller
        self.browser = browser

    async def run(self, max_steps=50):
        logger.info("Starting agent task...")
        try:
            await self.browser.launch()
            logger.info("Browser launched successfully.")
            result = await self.controller.execute(self.task, self.browser)
            logger.info("Controller task executed successfully.")
            return result
        except Exception as e:
            logger.exception(f"Agent encountered an error: {e}")
        finally:
            await self.browser.close()
            logger.info("Browser closed.")
