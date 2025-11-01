import json
from pathlib import Path
import markdown
from weasyprint import HTML, CSS
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
    document as both Markdown and PDF using the LLM.

    Returns:
        str: Path to the generated SRS PDF file.
    """
    try:
        logger.info("[SRSAgent] Starting SRS document generation...")

        # ----------------------------------------------------
        # 1️⃣ Prepare Prompts
        # ----------------------------------------------------
        system_prompt = load_prompt("system_base.md")
        user_prompt = load_prompt("srs.md").format(
            system=system_prompt,
            requirements_json=json.dumps(requirements, indent=2),
        )

        # ----------------------------------------------------
        # 2️⃣ Initialize LLM
        # ----------------------------------------------------
        llm = get_llm("srs")
        logger.info("[SRSAgent] Invoking model for SRS generation...")

        # ----------------------------------------------------
        # 3️⃣ Invoke LLM with token tracking
        # ----------------------------------------------------
        if hasattr(llm, "run_with_usage"):
            resp = llm.run_with_usage(user_prompt, "SRSAgent")
            md_doc = getattr(resp, "content", "").strip()
        else:
            resp = llm.invoke(user_prompt)
            md_doc = getattr(resp, "content", str(resp)).strip()

        if not md_doc:
            raise ValueError("Empty response from LLM while generating SRS document.")

        logger.info(f"[SRSAgent] Markdown generated ({len(md_doc)} characters)")

        # ----------------------------------------------------
        # 4️⃣ Clean Markdown Output
        # ----------------------------------------------------
        # Remove accidental code fences or artifacts
        if md_doc.startswith("```"):
            md_doc = md_doc.strip("` \n\t")
        if md_doc.lower().startswith("json"):
            md_doc = md_doc.replace("json", "", 1).strip()

        # ----------------------------------------------------
        # 5️⃣ Convert Markdown → HTML
        # ----------------------------------------------------
        html_str = markdown.markdown(
            md_doc,
            extensions=["tables", "fenced_code", "toc", "attr_list"],
            output_format="html5",
        )

        # Basic styling for readability
        css = CSS(string="""
            @page { size: A4; margin: 1in; }
            body { font-family: Arial, sans-serif; line-height: 1.5; font-size: 12px; }
            h1, h2, h3, h4 { color: #2A4B8D; }
            h1 { border-bottom: 2px solid #2A4B8D; padding-bottom: 5px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { border: 1px solid #666; padding: 6px; text-align: left; }
            th { background: #f0f4ff; }
            code { background-color: #f4f4f4; padding: 2px 4px; border-radius: 4px; }
        """)

        # ----------------------------------------------------
        # 6️⃣ Save Intermediate Markdown
        # ----------------------------------------------------
        ensure_dirs()
        md_path = Path(settings["paths"]["docs_dir"]) / "SRS.md"
        save_text(md_path, md_doc)
        logger.info(f"[SRSAgent] Markdown version saved at: {md_path}")

        # ----------------------------------------------------
        # 7️⃣ Generate PDF from HTML
        # ----------------------------------------------------
        pdf_path = Path(settings["paths"]["docs_dir"]) / "SRS.pdf"
        HTML(string=html_str).write_pdf(pdf_path, stylesheets=[css])
        logger.success(f"[SRSAgent] PDF written successfully: {pdf_path}")

        # ----------------------------------------------------
        # 8️⃣ Return Final Path
        # ----------------------------------------------------
        return str(pdf_path)

    except Exception as e:
        logger.exception(f"[SRSAgent] Failed to generate SRS: {e}")
        return ""
