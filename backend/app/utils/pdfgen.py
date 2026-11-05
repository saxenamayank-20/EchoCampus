"""A tiny PDF writer (plain text, Helvetica, A4). Used for the sample policies and in tests,
so we don't need a big pdf library just to make simple documents."""
import textwrap


def _escape(line: str) -> str:
    # ( ) and \ have a special meaning inside pdf text, so they get a backslash in front
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(pages: list[str], font_size: int = 11) -> bytes:
    """each string is one page. long lines are wrapped to fit the page width"""
    objects: list[bytes] = []
    page_ids = []
    font_id = 3 + 2 * len(pages)          # 1 = catalog, 2 = page list, then (page, content) pairs, then the font
    for i, text in enumerate(pages):
        lines = []
        for para in text.split("\n"):
            lines.extend(textwrap.wrap(para, 90) or [""])
        body = f"BT /F1 {font_size} Tf 14 TL 50 790 Td\n"
        body += "".join(f"({_escape(line)}) Tj T*\n" for line in lines[:52]) + "ET"
        stream = body.encode("latin-1", "replace")
        page_id, content_id = 3 + 2 * i, 4 + 2 * i
        page_ids.append(page_id)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_id} 0 R "
                       f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode())
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    head = [b"<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(pages)} >>".encode()]
    objects = head + objects + [b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)                       # the table that says where each object starts
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
