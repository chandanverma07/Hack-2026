import os
import re
import base64
import json
from loguru import logger
from pathlib import Path
from openai import OpenAI
from core.llm import tracker
from core.config import load_settings


def run_mindmap_agent(requirement_text: str) -> dict:
    """
    Generates both textual (Graphviz DOT) and visual (image) mind map
    from given requirements using GPT models.

    Returns:
        dict: {"text_map": str, "dot_path": str, "image_path": str}
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
    # 1️⃣ Generate Textual Mind Map (Graphviz DOT)
    # ----------------------------------------------------
    prompt_text = f"""
    You are a software architect and visualization expert.

    Based on the following requirements, create a clear, hierarchical **mind map** 
    in **Graphviz DOT format** showing:
    - Core system node
    - Major modules
    - Sub-functions under each module
    - Data flows or dependencies (use arrows)
    - Colorful, modular layout (rankdir=LR, filled shapes)

    Requirements:
    {requirement_text}

    Return only valid Graphviz DOT code, no Markdown or explanations.
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

        # --- Cleanup Markdown formatting ---
        clean_dot = re.sub(r"^```[a-zA-Z]*\s*", "", text_map)
        clean_dot = re.sub(r"```$", "", clean_dot)
        clean_dot = clean_dot.strip("` \n\r\t")

        # --- Ensure valid DOT structure ---
        if "digraph" not in clean_dot:
            clean_dot = f"digraph MindMap {{\n{clean_dot}\n}}"

        with open(dot_path, "w", encoding="utf-8") as f:
            f.write(clean_dot)

        text_map = clean_dot
        logger.info(f"[MindMapAgent] Text mind map saved: {dot_path}")

    except Exception as e:
        logger.exception("[MindMapAgent] Failed to generate text mind map.")
        text_map = "Error generating text mind map."

    # ----------------------------------------------------
    # 2️⃣ Generate Visual Mind Map (Image)
    # ----------------------------------------------------
    image_prompt = f"""
    Create a colorful mind map visualization based on this requirement.
    - Use distinct colors for each module.
    - Show parent-child relationships with arrows.
    - Include labels for each node.
    - Layout should be clean, centered, and organized.
    Requirements:
    {requirement_text}
    """

    try:
        logger.info("[MindMapAgent] Generating visual mind map image...")
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

    # ----------------------------------------------------
    # 3️⃣ Return Combined Output
    # ----------------------------------------------------
    return {
        "text_map": text_map,
        "dot_path": str(dot_path),
        "image_path": str(image_path),
    }
