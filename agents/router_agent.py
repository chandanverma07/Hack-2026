from agents.requirement_agent import run_requirement_agent
from agents.flow_agent import run_flow_agent
from agents.srs_agent import run_srs_agent
from agents.jira_story_agent import run_jira_story_agent
from agents.jira_post_agent import post_stories_to_jira
from core.config import load_settings
from core.logger import init_logger
from core.llm import tracker  # global token tracker shared across agents

logger = init_logger()
settings = load_settings()


def run_sequential_pipeline(user_input: str) -> dict:
    """
    Executes the full SDLC pipeline in sequence:
    1. Requirement Extraction
    2. Flow Diagram Generation
    3. SRS / Technical Documentation
    4. JIRA Story Creation (and optional posting)

    Returns:
        dict: Aggregated results (files, stories, token usage, errors)
    """
    logger.info("🚀 [RouterAgent] Starting Sequential SDLC Pipeline...")
    results = {}

    try:
        # --------------------------------
        # 1️⃣ REQUIREMENT GATHERING
        # --------------------------------
        logger.info("[RouterAgent] Step 1: Extracting Requirements...")
        results["requirements"] = run_requirement_agent(user_input)

        if "error" in results["requirements"]:
            logger.warning("[RouterAgent] Requirement agent returned an error.")
            raise RuntimeError("Requirement extraction failed")

        # --------------------------------
        # 2️⃣ FLOW DIAGRAM GENERATION
        # --------------------------------
        logger.info("[RouterAgent] Step 2: Generating Flow Diagram...")
        try:
            results["diagram_path"] = run_flow_agent(results["requirements"])
        except Exception as e:
            logger.warning(f"[RouterAgent] Flow generation skipped: {e}")
            results["diagram_path"] = ""

        # --------------------------------
        # 3️⃣ SRS / TECHNICAL DOCUMENTATION
        # --------------------------------
        if settings["features"].get("enable_pdf_gen", True):
            logger.info("[RouterAgent] Step 3: Generating SRS / Technical Document...")
            try:
                results["srs_path"] = run_srs_agent(results["requirements"])
            except Exception as e:
                logger.warning(f"[RouterAgent] SRS generation skipped: {e}")
                results["srs_path"] = ""

        # --------------------------------
        # 4️⃣ JIRA STORY GENERATION
        # --------------------------------
        logger.info("[RouterAgent] Step 4: Creating JIRA stories...")
        try:
            results["jira_stories"] = run_jira_story_agent(results["requirements"])
        except Exception as e:
            logger.warning(f"[RouterAgent] JIRA story generation skipped: {e}")
            results["jira_stories"] = []

        # --------------------------------
        # 5️⃣ OPTIONAL: POST TO JIRA
        # --------------------------------
        if settings["features"].get("enable_jira_post", False):
            logger.info("[RouterAgent] Step 5: Posting stories to JIRA...")
            try:
                results["jira_created"] = post_stories_to_jira(results["jira_stories"])
            except Exception as e:
                logger.warning(f"[RouterAgent] Failed to post to JIRA: {e}")
                results["jira_created"] = []

        # --------------------------------
        # 6️⃣ TOKEN USAGE SUMMARY
        # --------------------------------
        results["token_summary"] = tracker.summary()
        token_info = results["token_summary"]
        logger.info(
            f"[RouterAgent] Total tokens used: "
            f"input={token_info['total_input_tokens']}, "
            f"output={token_info['total_output_tokens']}, "
            f"approx_cost=${token_info['approx_cost_usd']}"
        )

        logger.success("✅ [RouterAgent] Sequential SDLC pipeline completed successfully.")
        return results

    except Exception as e:
        logger.exception(f"[RouterAgent] Pipeline failed: {e}")
        results["error"] = str(e)
        results["token_summary"] = tracker.summary()
        return results
