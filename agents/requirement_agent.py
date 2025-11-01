import json
import re
from core.llm import get_llm
from core.prompts_loader import load_prompt
from core.logger import init_logger

logger = init_logger()

# ======================================================
# 🔹 Requirement Agent
# ======================================================
def run_requirement_agent(problem_description: str) -> dict:
    """
    Generate structured software requirements using LLM.
    Returns both human-readable markdown and parsed JSON.
    """
    try:
        system = (
            "You are a senior business analyst generating structured requirements "
            "based on the provided problem statement."
        )

        # Load and format the prompt template
        prompt = load_prompt("requirements.md").format(
            system=system,
            problem_description=problem_description,
        )

        # Initialize the model
        llm = get_llm("requirement")
        logger.info("[RequirementAgent] Generating requirements...")

        # Get clean text output from LLM
        text = llm.invoke(prompt, agent_name="requirement")

        # Try to extract JSON block
        json_block = extract_json_from_text(text)
        parsed_json = safe_parse_json(json_block)

        # Fill missing keys for consistency
        parsed_json.setdefault("project_name", "Unknown Project")
        parsed_json.setdefault("functional_requirements", [])
        parsed_json.setdefault("non_functional_requirements", [])
        parsed_json.setdefault("actors", [])
        parsed_json.setdefault("assumptions", [])
        parsed_json.setdefault("modules", [])

        return {
            "readable_text": text.strip(),
            "parsed_json": parsed_json,
        }

    except Exception as e:
        logger.exception(f"[RequirementAgent] Failed: {e}")
        return {
            "readable_text": "",
            "parsed_json": {
                "project_name": "Unknown Project",
                "functional_requirements": [],
                "non_functional_requirements": [],
                "actors": [],
                "assumptions": [],
                "modules": [],
                "raw_response": str(e),
            },
        }


# ======================================================
# 🔹 Utility Helpers
# ======================================================
def extract_json_from_text(text: str) -> str:
    """
    Extracts JSON block from LLM markdown output.
    """
    match = re.search(r"```json(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        logger.warning("[RequirementAgent] No JSON block found in response.")
        return "{}"


def safe_parse_json(json_text: str) -> dict:
    """
    Safely parses JSON and returns {} if malformed.
    """
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        logger.warning("[RequirementAgent] Invalid JSON format in response.")
        return {}
