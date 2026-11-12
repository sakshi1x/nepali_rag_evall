"""Step 1b: split pages into chunks, one per Article (धारा) where a heading is found.
Heading pattern: line starting with Devanagari number + '.' e.g. '२८८. राजधानीः'
Long articles are split into ~300-word pieces with ~50-word overlap.
Output: data/processed/chunks.jsonl"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "data" / "processed" / "pages.jsonl"
OUT = ROOT / "data" / "processed" / "chunks.jsonl"

ARTICLE = re.compile(r"^([०-९]{1,3})\.\s*(.{1,80}?)\s*[ःः:]")
MAX_WORDS, OVERLAP = 300, 50


def split_long(words):
    if len(words) <= MAX_WORDS:
        return [words]
    step = MAX_WORDS - OVERLAP
    return [words[i:i + MAX_WORDS] for i in range(0, len(words) - OVERLAP, step)]


def main():
    pages = [json.loads(l) for l in PAGES.open(encoding="utf-8")]
    sections, cur = [], {"article": None, "title": "preamble/front", "page": 1, "lines": []}
    for p in pages:
        for line in p["text"].splitlines():
            m = ARTICLE.match(line)
            if m:
                sections.append(cur)
                cur = {"article": m.group(1), "title": m.group(2), "page": p["page"], "lines": []}
            cur["lines"].append(line)
    sections.append(cur)

    chunks = []
    for s in sections:
        words = " ".join(s["lines"]).split()
        if not words:
            continue
        for part_no, part in enumerate(split_long(words)):
            chunks.append({
                "chunk_id": f"c{len(chunks):04d}",
                "article": s["article"],
                "title": s["title"],
                "page": s["page"],
                "part": part_no,
                "text": " ".join(part),
            })
    with OUT.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"sections: {len(sections)}  chunks: {len(chunks)} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
