import json
import pandas as pd
import re
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
    from structured software requirements or SRS documents.

    Returns:
        list[dict]: List of JIRA story objects, each containing summary, description,
                    BDD content, role, and labels.
    """
    try:
        # -------------------------------
        # 1. Load Prompts
        # -------------------------------
        system_prompt = load_prompt("system_base.md")
        user_prompt = load_prompt("jira.md").format(
            system=system_prompt,
            requirements_json=json.dumps(requirements, indent=2)
        )

        # -------------------------------
        # 2. Initialize LLM
        # -------------------------------
        llm = get_llm()
        logger.info("[JiraStoryAgent] Generating user stories in BDD format...")

        # -------------------------------
        # 3. Invoke LLM with Token Tracking
        # -------------------------------
        if hasattr(llm, "run_with_usage"):
            resp = llm.run_with_usage(user_prompt, "JiraStoryAgent")
        else:
            resp = llm.invoke(user_prompt)

        text = resp.content if hasattr(resp, "content") else str(resp)

        # -------------------------------
        # 4. Clean JSON Markers (remove ```json ... ```)
        # -------------------------------
        cleaned_text = re.sub(r"```json|```", "", text).strip()

        # -------------------------------
        # 5. Parse LLM Response (JSON)
        # -------------------------------
        try:
            stories = json.loads(cleaned_text)
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
                    "role": "Developer",
                    "labels": ["auto", "sdlc"]
                }
            ]

        # -------------------------------
        # 6. Ensure Minimum Story Fields
        # -------------------------------
        cleaned_stories = []
        for s in stories:
            story = {
                "summary": s.get("summary", "Untitled Story"),
                "description": s.get("description", s.get("bdd", "No description provided.")),
                "bdd": s.get("bdd", ""),
                "role": s.get("role", "Developer"),
                "labels": s.get("labels", ["auto", "sdlc"])
            }
            cleaned_stories.append(story)

        # -------------------------------
        # 7. Save Intermediate Outputs (JSON + CSV)
        # -------------------------------
        if settings["features"].get("save_intermediate_json", True):
            ensure_dirs()

            # Save JSON
            json_path = "outputs/jira_stories.json"
            save_text(json_path, json.dumps(cleaned_stories, indent=2))
            logger.info(f"[JiraStoryAgent] Saved JSON -> {json_path}")

            # ✅ Save CSV
            try:
                df = pd.DataFrame(cleaned_stories)
                csv_path = "outputs/jira_stories.csv"
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                logger.info(f"[JiraStoryAgent] Saved CSV -> {csv_path}")
            except Exception as e:
                logger.warning(f"[JiraStoryAgent] Failed to save CSV: {e}")

        # -------------------------------
        # 8. Return Final Stories
        # -------------------------------
        logger.info(f"[JiraStoryAgent] Generated {len(cleaned_stories)} stories successfully.")
        return cleaned_stories

    except Exception as e:
        logger.exception(f"[JiraStoryAgent] Failed to generate JIRA stories: {e}")
        return []
