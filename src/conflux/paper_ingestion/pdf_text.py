"""PDF text extraction helpers for optional full-text paper promotion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .pdf_downloader import safe_pdf_id


@dataclass(slots=True)
class PDFTextResult:
    path: Path
    text: str
    status: str
    error: str = ""


def find_local_pdf(paper_id: str, pdf_dir: str | Path) -> Path | None:
    """Find a cached PDF by normalized paper id."""

    root = Path(pdf_dir)
    stem = safe_pdf_id(paper_id)
    candidates = [
        root / f"{stem}.pdf",
        root / f"{paper_id}.pdf",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def extract_pdf_text(path: str | Path, *, max_pages: int = 30) -> PDFTextResult:
    """Extract text from a PDF if pypdf is available."""

    pdf_path = Path(path)
    if not pdf_path.exists():
        return PDFTextResult(path=pdf_path, text="", status="missing", error="PDF file does not exist.")

    try:
        from pypdf import PdfReader
    except Exception as exc:
        return PDFTextResult(path=pdf_path, text="", status="unavailable", error=str(exc))

    try:
        reader = PdfReader(str(pdf_path))
        pages = []
        for page_number, page in enumerate(reader.pages[:max_pages], start=1):
            extracted = (page.extract_text() or "").strip()
            if extracted:
                pages.append(f"[[CONFLUX_PAGE:{page_number}]]\n{extracted}")
        text = "\n\n".join(pages)
        if not text:
            return PDFTextResult(path=pdf_path, text="", status="no_text", error="No extractable text found.")
        return PDFTextResult(path=pdf_path, text=text, status="success")
    except Exception as exc:
        return PDFTextResult(path=pdf_path, text="", status="failed", error=str(exc))
