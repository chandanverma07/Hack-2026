import json
from core.llm import get_llm
from core.prompts_loader import load_prompt
from core.logger import init_logger
from core.config import load_settings
from core.storage import ensure_dirs, save_text

logger = init_logger()
settings = load_settings()


def run_jira_story_agent(requirements: dict) -> list:
    """
    Generate JIRA-ready user stories in BDD (Behavior-Driven Development) format
    from structured software requirements.

    Returns:
        list[dict]: List of JIRA story objects, each containing summary, description, and BDD content.
    """
    try:
        # -------------------------------
        # 1️⃣ Load Prompts
        # -------------------------------
        system_prompt = load_prompt("system_base.md")
        user_prompt = load_prompt("jira.md").format(
            system=system_prompt,
            requirements_json=json.dumps(requirements, indent=2)
        )

        # -------------------------------
        # 2️⃣ Initialize LLM
        # -------------------------------
        llm = get_llm()
        logger.info("[JiraStoryAgent] Generating user stories (BDD format)...")

        # -------------------------------
        # 3️⃣ Invoke LLM with Token Tracking
        # -------------------------------
        if hasattr(llm, "run_with_usage"):
            resp = llm.run_with_usage(user_prompt, "JiraStoryAgent")
        else:
            resp = llm.invoke(user_prompt)

        text = resp.content if hasattr(resp, "content") else str(resp)

        # -------------------------------
        # 4️⃣ Parse LLM Response (JSON)
        # -------------------------------
        try:
            stories = json.loads(text)
            if not isinstance(stories, list):
                logger.warning("[JiraStoryAgent] Response was not a list. Wrapping as single story.")
                stories = [stories]

        except json.JSONDecodeError:
            logger.warning("[JiraStoryAgent] Invalid JSON response. Wrapping as single fallback story.")
            stories = [
                {
                    "summary": "Draft SDLC Story",
                    "description": text,
                    "bdd": text,
                    "labels": ["auto", "sdlc"],
                }
            ]

        # -------------------------------
        # 5️⃣ Ensure Minimum Story Fields
        # -------------------------------
        cleaned_stories = []
        for s in stories:
            story = {
                "summary": s.get("summary", "Untitled Story"),
                "description": s.get("description", s.get("bdd", "No description provided.")),
                "bdd": s.get("bdd", ""),
                "labels": s.get("labels", ["auto", "sdlc"]),
            }
            cleaned_stories.append(story)

        # -------------------------------
        # 6️⃣ Save Intermediate Output
        # -------------------------------
        if settings["features"].get("save_intermediate_json", True):
            ensure_dirs()
            save_text("outputs/jira_stories.json", json.dumps(cleaned_stories, indent=2))
            logger.info("[JiraStoryAgent] Saved intermediate stories -> outputs/jira_stories.json")

        # -------------------------------
        # 7️⃣ Return Final Stories
        # -------------------------------
        logger.success(f"[JiraStoryAgent] Generated {len(cleaned_stories)} stories successfully.")
        return cleaned_stories

    except Exception as e:
        logger.exception(f"[JiraStoryAgent] Failed to generate JIRA stories: {e}")
        return []
