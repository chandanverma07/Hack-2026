import os
import base64
import json
from loguru import logger
from pathlib import Path
from openai import OpenAI
from core.llm import tracker
from core.config import load_settings


def run_mindmap_agent(requirement_text: str) -> dict:
    """
    Generates both textual (Graphviz/Markdown tree) and visual mind map
    from given requirements using GPT models.
    Returns dict: {"text_map": str, "image_path": str}
    """
    settings = load_settings()
    api_key = settings["env"]["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
    vision_model = settings["env"].get("OPENAI_VISION_MODEL", "gpt-4o")
    text_model = settings["env"].get("OPENAI_MODEL", "gpt-4o-mini")

    output_dir = Path(settings["paths"]["diagrams_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / "mindmap.png"
    dot_path = output_dir / "mindmap.dot"

    # ----------------------------------------------------
    # 1️⃣ Generate Textual Mind Map (Markdown or Graphviz)
    # ----------------------------------------------------
    prompt_text = f"""
    You are a software architect and visualization expert.

    Based on the following requirements, create a clear, hierarchical **mind map** 
    in **Graphviz DOT format** showing:
    - Core system node
    - Major modules
    - Sub-functions under each module
    - Data flows or dependencies (use arrows)
    
    Keep the structure simple, no styling—just nodes and connections.

    Requirements:
    {requirement_text}

    Return only the Graphviz DOT code (no explanations).
    """

    text_map = ""
    try:
        response_text = client.chat.completions.create(
            model=text_model,
            messages=[
                {"role": "system", "content": "You are an expert in software architecture diagrams."},
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.3,
            max_tokens=1500,
        )

        text_map = response_text.choices[0].message.content.strip()
        tracker.log_agent("mindmap_text", 800, 500, 0.03)

        # Clean up and save Graphviz code if exists
        if "digraph" not in text_map:
            text_map = f"digraph MindMap {{\n{text_map}\n}}"

        with open(dot_path, "w", encoding="utf-8") as f:
            f.write(text_map)

        logger.info(f"[MindMapAgent] Text mind map saved: {dot_path}")
    except Exception as e:
        logger.exception("[MindMapAgent] Failed to generate text mind map.")
        text_map = "Error generating text mind map."

    # ----------------------------------------------------
    # 2️⃣ Generate Visual Mind Map Image
    # ----------------------------------------------------
    image_prompt = f"""
    Draw a mind map visualization showing key modules, submodules, and relationships
    from this requirement description.

    Use colored circles for main nodes, connecting arrows for relationships,
    and a clean hierarchy layout. Focus on clarity and structure.

    Requirements:
    {requirement_text}
    """

    try:
        logger.info("[MindMapAgent] Generating visual mind map...")
        response_img = client.images.generate(
            model="gpt-image-1",
            prompt=image_prompt,
            size="1024x1024"
        )

        image_base64 = response_img.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        tracker.log_agent("mindmap_image", 0, 300, 0.02)
        logger.info(f"[MindMapAgent] Visual mind map saved: {image_path}")
    except Exception as e:
        logger.exception(f"[MindMapAgent] Failed to generate visual mind map: {e}")
        image_path = ""

    return {
        "text_map": text_map,
        "dot_path": str(dot_path),
        "image_path": str(image_path),
    }
