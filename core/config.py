import os
import yaml
from loguru import logger
from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# 🔹 Load Environment Variables (.env)
# ============================================================
load_dotenv()


# ============================================================
# 🔹 Locate and Load settings.yaml
# ============================================================
def load_settings() -> dict:
    """
    Loads configuration from `config/settings.yaml` and expands env vars like ${VAR}.
    """
    try:
        config_path = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # Expand any ${ENV_VAR} placeholders before parsing YAML
        expanded_content = os.path.expandvars(raw_content)
        settings = yaml.safe_load(expanded_content)

        # Inject environment section if available
        settings["env"] = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "OPENAI_VISION_MODEL": os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        }

        logger.info(f"[Config] Loaded settings from {config_path}")
        return settings

    except Exception as e:
        logger.exception(f"[Config] Failed to load settings: {e}")
        return {}


# ============================================================
# 🔹 Example Helper: Get Model per Agent
# ============================================================
def get_agent_model(agent_name: str) -> str:
    """
    Returns the configured model name for a specific agent (e.g. requirement, flow, srs, jira).
    """
    settings = load_settings()
    try:
        model = settings.get("agents", {}).get(agent_name, {}).get("model")
        if not model:
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
        return model
    except Exception as e:
        logger.warning(f"[Config] Failed to resolve model for agent '{agent_name}': {e}")
        return os.getenv("OPENAI_MODEL", "gpt-4o")
