"""
core/vision_ocr.py
Provides OCR text extraction using OpenAI GPT-Vision models.
"""

import base64
import fitz  # PyMuPDF for PDF rendering
from openai import OpenAI
from core.logger import init_logger
from core.config import load_settings

logger = init_logger()
settings = load_settings()

def extract_text_from_image_bytes(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Sends image bytes to OpenAI Vision model for OCR text extraction.
    """
    client = OpenAI(api_key=settings["env"]["OPENAI_API_KEY"])
    model_name = settings["env"].get("OPENAI_VISION_MODEL", "gpt-4o")

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all readable text from this image or document. Return only plain text, no explanation."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )
        text = resp.choices[0].message.content
        return text.strip()

    except Exception as e:
        logger.exception(f"[VisionOCR] Failed to extract text: {e}")
        return ""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Converts first PDF page to PNG bytes and extracts text via Vision model.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            return ""

        all_text = ""
        for page in doc:
            pix = page.get_pixmap(dpi=180)
            image_bytes = pix.tobytes("png")
            page_text = extract_text_from_image_bytes(image_bytes)
            all_text += "\n" + page_text

        return all_text.strip()

    except Exception as e:
        logger.exception(f"[VisionOCR] PDF OCR failed: {e}")
        return ""
