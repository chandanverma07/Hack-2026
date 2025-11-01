from loguru import logger
from pathlib import Path
import sys

_INITIALIZED = False

def init_logger(level: str = "INFO", log_dir: str = "outputs/logs"):
    global _INITIALIZED
    if _INITIALIZED:
        return logger

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()

    # file log
    logger.add(
        Path(log_dir) / "app.log",
        rotation="1 week",
        level=level,
        backtrace=True,
        diagnose=True
    )

    # console log
    logger.add(sys.stdout, level=level)

    _INITIALIZED = True
    return logger
