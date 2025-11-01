from pathlib import Path
from core.config import load_settings
from core.logger import init_logger

settings = load_settings()
logger = init_logger()

def ensure_dirs():
    try:
        Path(settings["paths"]["outputs_dir"]).mkdir(parents=True, exist_ok=True)
        Path(settings["paths"]["diagrams_dir"]).mkdir(parents=True, exist_ok=True)
        Path(settings["paths"]["docs_dir"]).mkdir(parents=True, exist_ok=True)
        Path(settings["paths"]["logs_dir"]).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.exception(f"Error creating directories: {e}")
        raise

def save_text(path, content: str):
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Saved file: {path}")
        return str(path)
    except Exception as e:
        logger.exception(f"Error saving text to {path}: {e}")
        raise
