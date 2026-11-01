"""Splits page text into overlapping pieces small enough to embed and to quote.

~450 words is about 600 tokens (plan: 500-800). Pieces overlap by 60 words so a rule that
falls on a cut is still complete in one of them. Chunks never cross pages, so every
answer can cite an exact page number.
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    page: int          # 1-based, like the page number printed in the pdf
    index: int         # position in the whole document
    text: str


def chunk_pages(pages: list[str], max_words: int = 450, overlap: int = 60) -> list[Chunk]:
    chunks = []
    step = max_words - overlap
    for page_no, text in enumerate(pages, start=1):
        words = text.split()
        start = 0
        while start < len(words):
            piece = words[start:start + max_words]
            chunks.append(Chunk(page_no, len(chunks), " ".join(piece)))
            if start + max_words >= len(words):
                break
            start += step
    return chunks
