from pathlib import Path

from pypdf import PdfReader
from docx import Document


def parse_file(path: str, extension: str) -> str:
    ext = extension.lower()

    if ext == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    if ext in (".txt", ".md"):
        return Path(path).read_text(encoding="utf-8")

    raise ValueError(f"Unsupported file type: {ext}")
