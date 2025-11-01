import json
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

    Returns:
        str: Path to the generated PNG (preferred) or DOT file (fallback).
    """
    try:
        # -------------------------------
        # 1️⃣ Load Prompts
        # -------------------------------
        system_prompt = load_prompt("system_base.md")
        user_prompt = load_prompt("flow.md").format(
            system=system_prompt,
            requirements_json=json.dumps(requirements, indent=2)
        )

        # -------------------------------
        # 2️⃣ Initialize LLM
        # -------------------------------
        llm = get_llm()
        logger.info("[FlowAgent] Generating system flow diagram via LLM...")

        # -------------------------------
        # 3️⃣ Run Model (Token Tracked)
        # -------------------------------
        if hasattr(llm, "run_with_usage"):
            resp = llm.run_with_usage(user_prompt, "FlowAgent")
        else:
            resp = llm.invoke(user_prompt)

        dot_code = resp.content if hasattr(resp, "content") else str(resp)

        # Validate minimal Graphviz syntax
        if "digraph" not in dot_code:
            logger.warning("[FlowAgent] Output does not appear to be valid Graphviz DOT.")
            dot_code = f"digraph G {{\n  label=\"Generated Flow Diagram\";\n  node [shape=box];\n  LLM_Output -> Manual_Verification;\n}}"

        # -------------------------------
        # 4️⃣ Save DOT File
        # -------------------------------
        ensure_dirs()
        dot_path = Path(settings["paths"]["diagrams_dir"]) / "system_flow.dot"
        save_text(dot_path, dot_code)
        logger.info(f"[FlowAgent] DOT file saved: {dot_path}")

        # -------------------------------
        # 5️⃣ Attempt PNG Rendering
        # -------------------------------
        png_path = Path(settings["paths"]["diagrams_dir"]) / "system_flow.png"
        try:
            subprocess.run(
                ["dot", "-Tpng", str(dot_path), "-o", str(png_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.success(f"[FlowAgent] Diagram rendered successfully: {png_path}")
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
