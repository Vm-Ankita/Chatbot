import requests
from PIL import Image
from io import BytesIO
import pytesseract


def extract_text_from_image(url: str) -> str:
    """
    OCR with hard timeout.
    Never blocks ingestion.
    """
    try:
        r = requests.get(url, timeout=5)  # ⏱ HARD LIMIT
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception:
        return ""
