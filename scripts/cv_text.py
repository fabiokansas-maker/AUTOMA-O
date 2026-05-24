"""Extrai texto do CV PDF — tenta pypdf primeiro, fallback pypdfium2, depois vazio."""
from __future__ import annotations

import sys
from pathlib import Path


def extract_cv_text(pdf_path: Path) -> str:
    if not pdf_path.exists():
        print(f"[cv_text] PDF não encontrado: {pdf_path}", file=sys.stderr)
        return ""
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(str(pdf_path))
        return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except BaseException as e:  # noqa: BLE001 — pypdf pode lançar PanicException (BaseException)
        print(f"[cv_text] pypdf falhou ({type(e).__name__}: {e}), tentando pypdfium2", file=sys.stderr)
    try:
        import pypdfium2 as pdfium  # type: ignore
        pdf = pdfium.PdfDocument(str(pdf_path))
        return "\n".join(p.get_textpage().get_text_range() for p in pdf).strip()
    except BaseException as e:  # noqa: BLE001
        print(f"[cv_text] pypdfium2 falhou ({type(e).__name__}: {e}); retornando vazio", file=sys.stderr)
    return ""


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "cv" / "Curriculo_Fabio_Controladoria_0426.pdf"
    t = extract_cv_text(p)
    print(f"pages-extracted chars={len(t)}")
    print(t[:600])
