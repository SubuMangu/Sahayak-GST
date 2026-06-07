"""OCR stage (FR-003): image preprocessing + text recognition.

Real deployment uses OpenCV preprocessing (deskew/contrast/denoise) -> PaddleOCR/EasyOCR
fine-tuned on Indian tax invoices. To keep the MVP runnable everywhere (and CI light), the
default OCR is a no-op that returns a hint string; the LLM/mock stage does the structuring.
Swapping in PaddleOCR is a single function replacement here.
"""
from __future__ import annotations


def preprocess_and_ocr(file_bytes: bytes, mime: str, file_name: str) -> str:
    """Return recognised text for the document.

    The mock pipeline does not need real text (MockExtractor is seeded by the file hash),
    so we return a lightweight descriptor. Replace the body with PaddleOCR for production:

        from paddleocr import PaddleOCR
        result = PaddleOCR(lang='en').ocr(preprocessed_image)
        return "\\n".join(line[1][0] for block in result for line in block)
    """
    return f"[invoice document: {file_name} ({mime}), {len(file_bytes)} bytes]"
