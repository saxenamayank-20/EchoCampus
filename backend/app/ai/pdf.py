import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pages(data: bytes) -> list[str]:
    """text of each page (page 1 = index 0). empty list if the pdf can't be read"""
    try:
        reader = PdfReader(io.BytesIO(data))
        return [" ".join((page.extract_text() or "").split()) for page in reader.pages]
    except (PdfReadError, ValueError):
        return []
