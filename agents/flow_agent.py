import json
import re
import subprocess
from pathlib import Path
from core.llm import get_llm
from core.prompts_loader import load_prompt
from core.logger import init_logger
from core.config import load_settings
from core.storage import ensure_dirs, save_text

logger = init_logger()
settings = load_settings()


def run_flow_agent(requirements: dict) -> str:
    """
    Generate a Graphviz DOT script from structured requirements via LLM
    and render a PNG diagram (if Graphviz 'dot' is installed).

    Args:
        requirements (dict): Output from requirement_agent (contains both readable_text and parsed_json)
    Returns:
        str: Path to the generated PNG (preferred) or DOT file (fallback).
    """
    try:
        logger.info("[FlowAgent] Starting flow diagram generation...")

        # Handle both plain text and structured requirement output
        if isinstance(requirements, dict):
            requirements_json = (
                json.dumps(requirements.get("parsed_json", {}), indent=2)
                if requirements.get("parsed_json")
                else requirements.get("readable_text", "")
            )
        else:
            requirements_json = str(requirements)

        # Load prompt templates
        system_prompt = load_prompt("system_base.md")
        user_prompt = load_prompt("flow.md").format(
            system=system_prompt,
            requirements_json=requirements_json
        )

        # Initialize model
        llm = get_llm("flow")
        logger.info("[FlowAgent] Invoking model for flow generation...")

        # Generate flow diagram text
        response = llm.invoke(user_prompt, agent_name="flow")
        dot_code = getattr(response, "content", str(response)).strip()

        # Clean any markdown or code fences (```dot ... ```)
        clean_dot = re.sub(r"^```[a-zA-Z]*\s*", "", dot_code)
        clean_dot = re.sub(r"```$", "", clean_dot)
        clean_dot = clean_dot.strip("` \n\r\t")

        # Validate Graphviz syntax and fallback
        if not clean_dot or "digraph" not in clean_dot:
            logger.warning("[FlowAgent] No valid Graphviz DOT code detected. Using fallback structure.")
            clean_dot = (
                "digraph G {\n"
                "  label=\"System Flow\";\n"
                "  node [shape=box, style=filled, color=lightblue];\n"
                "  Start -> Process -> Output;\n"
                "}"
            )

        # Save .dot file
        ensure_dirs()
        dot_path = Path(settings["paths"]["diagrams_dir"]) / "system_flow.dot"
        save_text(dot_path, clean_dot)
        logger.info(f"[FlowAgent] DOT file saved at {dot_path}")

        # Try rendering to PNG
        png_path = Path(settings["paths"]["diagrams_dir"]) / "system_flow.png"
        try:
            subprocess.run(
                ["dot", "-Tpng", str(dot_path), "-o", str(png_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info(f"[FlowAgent] Diagram rendered successfully: {png_path}")
            return str(png_path)

        except FileNotFoundError:
            logger.warning("[FlowAgent] Graphviz 'dot' not found. Returning DOT file instead.")
            return str(dot_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"[FlowAgent] Graphviz rendering failed: {e.stderr.decode('utf-8', 'ignore')}")
            return str(dot_path)
        except Exception as e:
            logger.exception(f"[FlowAgent] Unexpected rendering error: {e}")
            return str(dot_path)

    except Exception as e:
        logger.exception(f"[FlowAgent] Failed to generate flow diagram: {e}")
        return ""
