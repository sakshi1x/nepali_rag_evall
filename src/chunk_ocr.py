"""Step 1c (directive-v2): clean OCR pages and chunk by Article (धारा).
Run only after src/ocr_quality.py passes.
Input : data/ocr/pages_ocr*.jsonl
Output: data/ocr/chunks_ocr.jsonl, plus a summary printed to screen."""
import json, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "ocr"
ARTICLE = re.compile(r"^([०-९]{1,3})\s*[.,]\s*(.{1,80}?)\s*[ःः:]")
# OCR often drops the Article number (it sits in the left margin). Heading without number:
# a short title ending in ः/: followed by "(१)". The number is NOT guessed; article stays None.
UNNUMBERED = re.compile(r"^[.,\s]*([^()०-९\d]{2,60}?)\s*[ःः:]\s*\(१\)")
MAX_WORDS, OVERLAP = 300, 50
D2A = str.maketrans("०१२३४५६७८९", "0123456789")


def is_noise(line: str) -> bool:
    """Header/footer garbage: lines where Devanagari is less than 30% of the letters, or bare page numbers."""
    letters = [ch for ch in line if ch.isalpha() or "ऀ" <= ch <= "ॿ"]
    if not letters:
        return True
    dev = sum("ऀ" <= ch <= "ॿ" for ch in letters)
    return dev / len(letters) < 0.3


def load_pages():
    pages = {}
    for f in sorted(D.glob("pages_ocr*.jsonl")):
        for l in f.open(encoding="utf-8"):
            r = json.loads(l)
            pages[r["page"]] = r["text"]
    return [{"page": p, "text": t} for p, t in sorted(pages.items())]


def main():
    pages = load_pages()
    dropped = 0
    sections, cur = [], {"article": None, "title": "preamble/front", "page": 1, "lines": []}
    for p in pages:
        for line in (l.strip() for l in p["text"].splitlines()):
            if not line:
                continue
            if is_noise(line):
                dropped += 1
                continue
            m = ARTICLE.match(line)
            u = None if m else UNNUMBERED.match(line)
            if m or u:
                sections.append(cur)
                cur = {"article": m.group(1) if m else None, "title": (m or u).group(m and 2 or 1).strip(),
                       "page": p["page"], "lines": [], "number_missing_in_ocr": not m}
            cur["lines"].append(line)
    sections.append(cur)

    chunks = []
    for s in sections:
        words = " ".join(s["lines"]).split()
        step = MAX_WORDS - OVERLAP
        parts = [words] if len(words) <= MAX_WORDS else [words[i:i + MAX_WORDS] for i in range(0, len(words) - OVERLAP, step)]
        for n, part in enumerate(parts):
            if part:
                chunks.append({"chunk_id": f"o{len(chunks):04d}", "article": s["article"], "title": s["title"],
                               "page": s["page"], "part": n, "number_missing_in_ocr": s.get("number_missing_in_ocr", False),
                               "text": " ".join(part)})
    with (D / "chunks_ocr.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    lens = sorted(len(c["text"].split()) for c in chunks)
    nums = [int(c["article"].translate(D2A)) for c in chunks if c["article"] and c["part"] == 0]
    print(f"pages: {len(pages)}  noise lines dropped: {dropped}  chunks: {len(chunks)}")
    print(f"words per chunk min/avg/max: {lens[0]} / {sum(lens)//len(lens)} / {lens[-1]}")
    unnum = sum(1 for c in chunks if c["number_missing_in_ocr"] and c["part"] == 0)
    print(f"article headings with number: {len(nums)} (unique {len(set(nums))}); headings found without number (OCR dropped it): {unnum}")
    print(f"total headings: {len(nums) + unnum} (the Constitution has 308 Articles)")
    print(f"numbers not seen: {len(set(range(1,309)) - set(nums))}")
    random.seed(42)
    for c in random.sample(chunks, 3):
        print(f"\n[{c['chunk_id']}] article {c['article']} '{c['title']}' page {c['page']}\n{c['text'][:300]}")


if __name__ == "__main__":
    main()
