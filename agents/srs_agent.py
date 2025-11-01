import json
from pathlib import Path
import markdown
from weasyprint import HTML
from core.llm import get_llm
from core.prompts_loader import load_prompt
from core.logger import init_logger
from core.config import load_settings
from core.storage import ensure_dirs, save_text

logger = init_logger()
settings = load_settings()


def run_srs_agent(requirements: dict) -> str:
    """
    Generate an IEEE-style Software Requirements Specification (SRS)
    document as a PDF using the LLM. Produces intermediate Markdown for transparency.

    Returns:
        str: Path to the generated SRS PDF file.
    """
    try:
        # -------------------------------
        # 1️⃣ Load Prompts
        # -------------------------------
        system_prompt = load_prompt("system_base.md")
        user_prompt = load_prompt("srs.md").format(
            system=system_prompt,
            requirements_json=json.dumps(requirements, indent=2),
        )

        # -------------------------------
        # 2️⃣ Initialize LLM
        # -------------------------------
        llm = get_llm()
        logger.info("[SRSAgent] Generating IEEE-style SRS markdown...")

        # -------------------------------
        # 3️⃣ Invoke LLM (with token tracking)
        # -------------------------------
        if hasattr(llm, "run_with_usage"):
            resp = llm.run_with_usage(user_prompt, "SRSAgent")
        else:
            resp = llm.invoke(user_prompt)

        md_doc = resp.content if hasattr(resp, "content") else str(resp)
        if not md_doc.strip():
            raise ValueError("Empty response from LLM while generating SRS.")

        # -------------------------------
        # 4️⃣ Convert Markdown → HTML
        # -------------------------------
        html_str = markdown.markdown(md_doc, output_format="html5")

        # -------------------------------
        # 5️⃣ Save intermediate Markdown (for inspection)
        # -------------------------------
        ensure_dirs()
        md_path = Path(settings["paths"]["docs_dir"]) / "SRS.md"
        save_text(md_path, md_doc)
        logger.info(f"[SRSAgent] Markdown version saved at: {md_path}")

        # -------------------------------
        # 6️⃣ Generate PDF from HTML
        # -------------------------------
        pdf_path = Path(settings["paths"]["docs_dir"]) / "SRS.pdf"
        HTML(string=html_str).write_pdf(pdf_path)
        logger.success(f"[SRSAgent] PDF written to {pdf_path}")

        # -------------------------------
        # 7️⃣ Return final path
        # -------------------------------
        return str(pdf_path)

    except Exception as e:
        logger.exception(f"[SRSAgent] Failed to generate SRS: {e}")
        return ""
