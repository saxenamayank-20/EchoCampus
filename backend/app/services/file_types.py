import io
import zipfile

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def detect_file_type(data: bytes) -> tuple[str, str] | None:
    """looks at the first bytes (magic bytes), not the file name. returns (mime, extension) or None"""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf", ".pdf"
    if data.startswith(b"PK\x03\x04") and _is_docx(data):
        return DOCX_MIME, ".docx"
    return None


def _is_docx(data: bytes) -> bool:
    # docx is a zip, but so is any archive. a real docx has word/document.xml inside
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
    except zipfile.BadZipFile:
        return False
    return "word/document.xml" in names and "[Content_Types].xml" in names
