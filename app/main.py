import sys
from pathlib import Path

# --- Ensure project root is in PYTHONPATH ---
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

import time
import base64
import re
import io
import json
import streamlit as st
import fitz  # PyMuPDF for PDF → image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from openai import OpenAI

# ---- Core Imports ----
from core.config import load_settings
from core.logger import init_logger
from core.llm import tracker

# ---- Agent Imports ----
from agents.router_agent import run_sequential_pipeline
from agents.requirement_agent import run_requirement_agent
from agents.flow_agent import run_flow_agent
from agents.srs_agent import run_srs_agent
from agents.jira_story_agent import run_jira_story_agent
from agents.mindmap_agent import run_mindmap_agent

# ---- LangGraph ----
from graphs.sdlc_graph import run_sdlc_graph


# ============================================================
# Initialization
# ============================================================
settings = load_settings()
logger = init_logger(settings["env"]["LOG_LEVEL"])

st.set_page_config(
    page_title=settings["ui"]["title"],
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title(settings["ui"]["title"])
st.markdown("<h4 style='color:grey'>Multi-Agent SDLC Automation Platform</h4>", unsafe_allow_html=True)
st.markdown("---")


# ============================================================
# Sidebar Controls
# ============================================================
st.sidebar.title("Control Panel")

agent_option = st.sidebar.selectbox(
    "Select Agent Mode:",
    [
        "Requirement Gathering",
        "Flow Diagram Generation",
        "Mind Map Generator",
        "SRS / Technical Document",
        "JIRA Story Generator",
        "Sequential Pipeline (All Agents)",
        "LangGraph Pipeline",
    ],
)

st.sidebar.markdown("---")
enable_jira = st.sidebar.checkbox("Enable JIRA Posting", value=False)
st.sidebar.caption("Configure LLM and settings in `.env` or `config/settings.yaml`")

# Token usage monitor
st.sidebar.markdown("### Token Usage Monitor")
progress_bar = st.sidebar.progress(0)
token_info = st.sidebar.empty()


def update_token_ui(summary: dict):
    total = summary["total_input_tokens"] + summary["total_output_tokens"]
    cost = summary["approx_cost_usd"]
    agent_count = len(summary["agents"])
    progress_bar.progress(min(agent_count / 6.0, 1.0))
    token_info.markdown(
        f"""
        Agents Completed: {agent_count}  
        Total Tokens: {total:,}  
        Input: {summary['total_input_tokens']:,} | Output: {summary['total_output_tokens']:,}  
        Approx. Cost: **${cost}**
        """
    )


tracker.set_callback(update_token_ui)


# ============================================================
# OCR Helpers (Vision Model)
# ============================================================
def extract_text_with_vision(file_bytes: bytes, mime_type: str) -> str:
    """Extract readable text from image or PDF using GPT Vision."""
    try:
        client = OpenAI(api_key=settings["env"]["OPENAI_API_KEY"])
        model_name = settings["env"].get("OPENAI_VISION_MODEL", "gpt-4o")
        b64_image = base64.b64encode(file_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract readable text from this document. Return plain text only."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_image}"}},
                    ],
                }
            ],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.exception(f"[VisionOCR] Failed: {e}")
        st.error("Vision model failed to extract text.")
        return ""


def pdf_to_images_bytes(pdf_bytes: bytes) -> list:
    """Convert all PDF pages to image bytes."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return [page.get_pixmap(dpi=180).tobytes("png") for page in doc]
    except Exception as e:
        logger.exception(f"[PDF Conversion] Failed: {e}")
        return []


# ============================================================
# Display Requirement Output
# ============================================================
def display_requirement_output(result: dict):
    """Display structured requirement output and formatted PDF download."""
    readable_text = result.get("readable_text", "").replace("\\n", "\n").strip()
    parsed_json = result.get("parsed_json", {})

    # Section 1 - JSON View
    if parsed_json:
        st.markdown("### Structured JSON Output")
        st.json(parsed_json)

    # Section 2 - Text Report
    if readable_text:
        st.markdown("---")
        st.markdown("### Detailed Requirement Report")
        st.markdown(readable_text)
    else:
        st.warning("No readable report text found.")

    # Section 3 - PDF Export
    pdf_buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    story = [Paragraph(readable_text, styles["Normal"])]
    doc.build(story)
    st.download_button(
        "Download as PDF",
        data=pdf_buffer.getvalue(),
        file_name="Requirements_Report.pdf",
        mime="application/pdf",
    )


# ============================================================
# Input Section
# ============================================================
st.subheader("Input Your Problem Statement")
input_mode = st.radio("Select Input Type:", ["Enter Text", "Upload (PDF / Image)"], horizontal=True)
user_input = ""

if input_mode == "Enter Text":
    user_input = st.text_area(
        "Describe your system requirement:",
        height=180,
        placeholder="Example: Build an AI-powered attendance tracking system...",
    )
else:
    uploaded_file = st.file_uploader("Upload a PDF or Image:", type=["pdf", "jpg", "jpeg", "png"])
    if uploaded_file:
        with st.spinner("Extracting text using GPT Vision..."):
            try:
                raw_bytes = uploaded_file.read()
                if uploaded_file.name.lower().endswith(".pdf"):
                    pages = pdf_to_images_bytes(raw_bytes)
                    user_input = "\n".join(extract_text_with_vision(p, "image/png") for p in pages)
                else:
                    user_input = extract_text_with_vision(raw_bytes, f"image/{uploaded_file.name.split('.')[-1]}")
                if user_input:
                    st.success("Text extracted successfully.")
                    with st.expander("View Extracted Text"):
                        st.text_area("Extracted Text", user_input, height=250)
                else:
                    st.warning("No text extracted.")
            except Exception as e:
                st.error(f"OCR failed: {e}")
                logger.exception(e)


# ============================================================
# Action Section
# ============================================================
st.markdown("---")
st.subheader("Run Agent")

if st.button("Execute"):
    if not user_input.strip():
        st.warning("Please enter or upload input before running.")
    else:
        start_time = time.time()
        tracker.reset()

        with st.spinner("Running selected agent..."):
            try:
                # Requirement Agent
                if "Requirement" in agent_option:
                    result = run_requirement_agent(user_input)
                    st.success("Requirements extracted successfully.")
                    display_requirement_output(result)

                # Flow Diagram
                elif "Flow" in agent_option:
                    req = run_requirement_agent(user_input)
                    diagram_path = run_flow_agent(req)
                    if Path(diagram_path).exists():
                        st.image(diagram_path, caption="Generated Flow Diagram", use_container_width=True)

                # Mind Map
                elif "Mind Map" in agent_option:
                    req = run_requirement_agent(user_input)
                    st.success("Requirements extracted. Generating mind map...")
                    mindmap = run_mindmap_agent(req.get("readable_text", user_input))
                    st.code(mindmap["text_map"], language="dot")
                    if Path(mindmap["image_path"]).exists():
                        st.image(mindmap["image_path"], caption="Visual Mind Map", use_container_width=True)

                # SRS
                elif "SRS" in agent_option:
                    req = run_requirement_agent(user_input)
                    pdf_path = run_srs_agent(req)
                    if Path(pdf_path).exists():
                        st.download_button("Download SRS PDF", data=open(pdf_path, "rb"), file_name="SRS_Document.pdf")

                # JIRA Stories
                elif "JIRA" in agent_option:
                    req = run_requirement_agent(user_input)
                    stories = run_jira_story_agent(req)
                    st.json(stories)

                # Sequential Full Pipeline
                elif "Sequential" in agent_option:
                    full_result = run_sequential_pipeline(user_input)
                    st.json(full_result)

                # LangGraph
                elif "LangGraph" in agent_option:
                    graph_result = run_sdlc_graph(user_input)
                    st.json(graph_result)

            except Exception as e:
                st.error(f"Error executing agent: {e}")
                logger.exception(e)

        # Token Summary
        summary = tracker.summary()
        if summary["total_input_tokens"] > 0:
            st.markdown("---")
            st.markdown("### Token Usage Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("Input Tokens", f"{summary['total_input_tokens']:,}")
            c2.metric("Output Tokens", f"{summary['total_output_tokens']:,}")
            c3.metric("Approx. Cost (USD)", f"${summary['approx_cost_usd']}")
            st.json(summary["agents"])

        st.info(f"Execution Time: {round(time.time() - start_time, 2)} seconds")


# ============================================================
# Footer
# ============================================================
st.markdown("---")
st.caption("Built using Streamlit · LangGraph · GPT Vision · Loguru")
