"""Optional PDF download helpers inspired by AcademyHunter."""

from __future__ import annotations

import urllib.request
from pathlib import Path


class PDFDownloader:
    """Download paper PDFs into a local cache.

    Network access is intentionally caller-controlled. The class is used only
    when CLI users opt into downloading PDFs.
    """

    def __init__(self, download_dir: str | Path, timeout: float = 30.0):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def download(self, paper_id: str, pdf_url: str = "") -> Path | None:
        """Download one PDF, returning the local path or None on failure."""

        safe_id = safe_pdf_id(paper_id)
        local_path = self.download_dir / f"{safe_id}.pdf"
        if local_path.exists():
            return local_path

        url = pdf_url.strip() or arxiv_pdf_url(safe_id)
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Conflux/0.1 GraduateResearchCopilot"},
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content = response.read()
            if not content.startswith(b"%PDF"):
                return None
            local_path.write_bytes(content)
            return local_path
        except Exception:
            return None

    def download_batch(self, papers: list[tuple[str, str]]) -> dict[str, Path | None]:
        """Download a batch of `(paper_id, pdf_url)` pairs."""

        return {paper_id: self.download(paper_id, pdf_url) for paper_id, pdf_url in papers}


def arxiv_pdf_url(paper_id: str) -> str:
    """Build an arXiv PDF URL for a normalized paper id."""

    return f"https://arxiv.org/pdf/{safe_pdf_id(paper_id)}.pdf"


def safe_pdf_id(value: str) -> str:
    """Normalize common arXiv URL/id shapes into a filesystem-safe PDF stem."""

    text = value.strip()
    if "/abs/" in text:
        text = text.rsplit("/abs/", 1)[1]
    if "/pdf/" in text:
        text = text.rsplit("/pdf/", 1)[1]
    if text.endswith(".pdf"):
        text = text[:-4]
    return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in text).strip("-") or "unknown"
