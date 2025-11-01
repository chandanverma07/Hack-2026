from pathlib import Path
from core.logger import init_logger

logger = init_logger()

PROMPTS_DIR = Path("prompts")

def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        logger.error(f"Prompt file not found: {path}")
        raise FileNotFoundError(f"Prompt file not found: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.exception(f"Error reading prompt {name}: {e}")
        raise
