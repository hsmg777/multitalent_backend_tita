# app/ext/pdf_reader.py
import pdfplumber
from pdf2image import convert_from_path
import numpy as np

_OCR_MIN_CHARS = 40          
_POPPLER_PATH = None        

try:
    import easyocr
    _reader = easyocr.Reader(['es'], gpu=False)
except Exception:
    _reader = None 


def _ocr_page(file_path: str, page_number: int, dpi: int = 300) -> str:
    """
    Convierte una página del PDF a imagen y aplica OCR con easyocr.
    NO usa variables de entorno; usa defaults internos.
    """
    try:
        images = convert_from_path(
            file_path,
            dpi=dpi,
            first_page=page_number,
            last_page=page_number,
            poppler_path=_POPPLER_PATH, 
        )
        if not images or _reader is None:
            return ""
        img = images[0]
        result = _reader.readtext(np.array(img))
        return " ".join((frag[1] for frag in result)) if result else ""
    except Exception:
        return ""


def extract_text_from_pdf(path: str) -> str:
    """
    Lee TODO el PDF:
      1) Intenta texto embebido con pdfplumber.
      2) Si una página viene vacía o muy corta, hace fallback a OCR de esa página.
    No recorta el resultado final.
    """
    parts = []
    with pdfplumber.open(path) as pdf:
        for idx, p in enumerate(pdf.pages, start=1):
            txt = (p.extract_text() or "").strip()
            if len(txt) < _OCR_MIN_CHARS:
                ocr_txt = _ocr_page(path, idx)
                if len(ocr_txt) >= len(txt):
                    txt = ocr_txt.strip()
            parts.append(txt)
    return "\n".join(parts)
