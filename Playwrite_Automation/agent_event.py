import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use.agent import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.controller_event import Controller
from browser_use.browser.task_prompt_event import build_event_prompt

load_dotenv()

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/event_automation.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

@dataclass
class EventConfig:
    openai_api_key: str
    headless: bool = False
    model: str = "gpt-4o"
    event_url: str = os.getenv("EVENT_URL")
    event_username: str = os.getenv("EVENT_USERNAME")
    event_password: str = os.getenv("EVENT_PASSWORD")

    def validate(self):
        if not all([
            self.openai_api_key,
            self.event_url,
            self.event_username,
            self.event_password,
        ]):
            raise ValueError("Missing one or more required environment variables.")

def create_event_agent(config: EventConfig) -> Agent:
    llm = ChatOpenAI(model=config.model, api_key=config.openai_api_key)
    browser = Browser(
        config=BrowserConfig(
            headless=config.headless,
            extra_chromium_args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
    )
    controller = Controller(
        base_url=config.event_url,
        username=config.event_username,
        password=config.event_password,
    )
    full_task = build_event_prompt(config)
    return Agent(task=full_task, llm=llm, controller=controller, browser=browser)

async def main():
    config = EventConfig(openai_api_key=os.getenv("OPENAI_API_KEY"), headless=False)
    try:
        config.validate()
    except ValueError as e:
        logger.error(str(e))
        return

    agent = create_event_agent(config)
    try:
        logger.info(f"Starting Event automation for: {config.event_url}")
        await agent.run(max_steps=50)
        logger.info("Event automation completed successfully.")
    except Exception as e:
        logger.exception(f"Automation failed: {e}")
    finally:
        logger.info("Automation run finished.")

if __name__ == "__main__":
    asyncio.run(main())
