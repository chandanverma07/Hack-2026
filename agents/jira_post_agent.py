import os
import time
import requests
from core.logger import init_logger
from core.config import load_settings

logger = init_logger()
settings = load_settings()


def post_stories_to_jira(stories: list, project_key: str = None) -> list:
    """
    Posts user stories to a configured JIRA project using REST API.

    Args:
        stories (list): List of story dicts (summary, description, etc.)
        project_key (str): Optional override for project key.
    Returns:
        list: List of created JIRA issue keys (if successful).
    """
    try:
        # -------------------------------
        # 1️⃣ Load credentials
        # -------------------------------
        base = os.getenv("JIRA_BASE_URL")
        email = os.getenv("JIRA_EMAIL")
        token = os.getenv("JIRA_API_TOKEN")
        project_key = project_key or "SDLC"

        if not (base and email and token):
            logger.warning("[JiraPostAgent] Missing JIRA credentials; skipping post.")
            return []

        if not stories:
            logger.warning("[JiraPostAgent] No stories provided for posting.")
            return []

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        created = []
        failed = []

        # -------------------------------
        # 2️⃣ Post each story sequentially
        # -------------------------------
        for idx, story in enumerate(stories, start=1):
            try:
                payload = {
                    "fields": {
                        "project": {"key": project_key},
                        "summary": story.get("summary", f"Auto-Generated Story {idx}"),
                        "description": story.get("bdd", story.get("description", "")),
                        "labels": story.get("labels", ["auto", "sdlc"]),
                        "issuetype": {"name": "Story"},
                    }
                }

                url = f"{base}/rest/api/3/issue"
                logger.info(f"[JiraPostAgent] Creating JIRA story {idx}/{len(stories)} → {url}")

                resp = requests.post(url, json=payload, auth=(email, token), headers=headers)
                if resp.status_code in (200, 201):
                    issue_key = resp.json().get("key", "UNKNOWN_KEY")
                    created.append(issue_key)
                    logger.success(f"[JiraPostAgent] ✅ Created issue {issue_key}")
                elif resp.status_code == 429:  # rate-limited
                    logger.warning("[JiraPostAgent] Rate-limited by JIRA API, retrying after delay...")
                    time.sleep(3)
                    continue
                else:
                    failed.append({
                        "summary": story.get("summary"),
                        "status_code": resp.status_code,
                        "error": resp.text[:300],
                    })
                    logger.error(
                        f"[JiraPostAgent] ❌ Failed: {resp.status_code} | {resp.text[:300]}"
                    )

            except requests.RequestException as e:
                logger.exception(f"[JiraPostAgent] Network error posting story: {e}")
                failed.append({"summary": story.get("summary"), "error": str(e)})

            except Exception as e:
                logger.exception(f"[JiraPostAgent] Unexpected error posting story: {e}")
                failed.append({"summary": story.get("summary"), "error": str(e)})

        # -------------------------------
        # 3️⃣ Summary Logging
        # -------------------------------
        if created:
            logger.info(f"[JiraPostAgent] Successfully created {len(created)} stories.")
        if failed:
            logger.warning(f"[JiraPostAgent] {len(failed)} stories failed to post.")

        summary = {
            "project": project_key,
            "total_stories": len(stories),
            "created_count": len(created),
            "failed_count": len(failed),
            "created_keys": created,
            "failed": failed,
        }

        logger.info(f"[JiraPostAgent] Summary: {summary}")
        return created

    except Exception as e:
        logger.exception(f"[JiraPostAgent] Critical failure posting to JIRA: {e}")
        return []
