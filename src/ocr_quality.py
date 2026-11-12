"""Step 1b (directive-v2): quality gate on the OCR text. Must pass before chunking.
Input : data/ocr/pages_ocr*.jsonl
Output: data/ocr/ocr_quality_report.txt (also printed). Exit code 1 if the gate fails."""
import json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "ocr"
SIGN = "ा-ौॢॣ"
BROKEN = ["बमोजजम", "िुनेछ", "गनव", "कायव", "प्रमिमनमध"]
MAX_BAD_PER_100 = 0.5
INVISIBLE = dict.fromkeys(map(ord, "\u200c\u200d"))  # zero-width non-joiner / joiner, ignored when matching quotes  # vowel signs in impossible positions, per 100 words


def load_pages():
    pages = {}
    for f in sorted(D.glob("pages_ocr*.jsonl")):
        for l in f.open(encoding="utf-8"):
            r = json.loads(l)
            pages[r["page"]] = r["text"]
    return dict(sorted(pages.items()))


def main():
    pages = load_pages()
    text = " ".join(" ".join(t.split()) for t in pages.values())
    words = len(text.split())
    bad_pos = len(re.findall(rf"(?:^|\s)[{SIGN}]", text)) + len(re.findall(rf"[{SIGN}][{SIGN}]", text))
    rate = 100 * bad_pos / max(words, 1)
    base = (ROOT / "baseline-qa.md").read_text(encoding="utf-8")
    match_text = text.translate(INVISIBLE)
    quotes = [" ".join(q.translate(INVISIBLE).split()) for q in re.findall(r'\*\*Evidence from text:\*\*\s*"(.+?)"', base)]
    missing_pages = sorted(set(range(1, 184)) - set(pages))
    lines = [f"pages OCR'd: {len(pages)} / 183   missing: {missing_pages[:20]}",
             f"words: {words}",
             "known broken forms (must be ~0):",
             *[f"  {w}: {text.count(w)}" for w in BROKEN],
             f"vowel signs in impossible positions: {bad_pos} ({rate:.2f} per 100 words, limit {MAX_BAD_PER_100})",
             "baseline evidence quotes:",
             *[("  FOUND   " if q in match_text else "  MISSING ") + q[:70] for q in quotes]]
    quotes_ok = all(q in match_text for q in quotes)
    passed = (not missing_pages and all(text.count(w) <= 2 for w in BROKEN) and rate <= MAX_BAD_PER_100 and quotes_ok)
    lines.append(f"GATE: {'PASS' if passed else 'FAIL'}")
    random.seed(42)
    lines.append("\n--- 3 random pages (compare with the PDF on screen) ---")
    for p in random.sample(list(pages), 3):
        lines.append(f"\n[page {p}]\n" + pages[p][:500])
    report = "\n".join(lines)
    (D / "ocr_quality_report.txt").write_text(report + "\n", encoding="utf-8")
    print(report)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
