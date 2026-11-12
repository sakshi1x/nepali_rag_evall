"""Step 1a: extract text page by page from the Constitution PDF.
Output: data/processed/pages.jsonl  ({"page": 1-based, "text": ...})
Uses pypdf (PyMuPDF could not be installed in the build environment)."""
import json, re, sys, unicodedata
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF = next((ROOT / "assets").glob("*.pdf"))
OUT = ROOT / "data" / "processed" / "pages.jsonl"

HEADER = re.compile(r"www\.lawcommission\.gov\.np")


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = HEADER.sub("", text)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not re.fullmatch(r"\d+", ln)]  # drop page numbers
    return "\n".join(lines)


def main():
    reader = PdfReader(str(PDF))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for i, page in enumerate(reader.pages, start=1):
            f.write(json.dumps({"page": i, "text": clean(page.extract_text() or "")}, ensure_ascii=False) + "\n")
    print(f"pages: {len(reader.pages)} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
