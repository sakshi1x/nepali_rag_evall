"""Step 1c: drop broken sentences, keep only sentences with no corruption signs.
Does NOT fix or guess any characters. Original pages.jsonl / chunks.jsonl stay unchanged.
Input : data/processed/chunks.jsonl
Output: data/processed/chunks_clean.jsonl     (per chunk: only the clean sentences)
        data/processed/chunks_rejected.jsonl  (every dropped sentence, with chunk_id, page, reason)
        data/processed/validation_report.txt"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "data" / "processed"
MIN_WORDS_SENT = 5      # shorter sentences are dropped (reason: too short)
MIN_WORDS_CHUNK = 15    # a clean chunk needs at least this many words to be usable for Q&A

SIGN = "ा-ौॢॣ"  # dependent vowel signs (matras)
RULES = [
    ("vowel sign at start of a word", re.compile(rf"(?:^|\s)[{SIGN}]")),
    ("two vowel signs in a row", re.compile(rf"[{SIGN}][{SIGN}]")),
]
# Broken forms seen in Step 1 (correct form in comment). Used only to DETECT, never to replace.
KNOWN_BROKEN = ["बमोजजम",   # बमोजिम
                "िुन",      # हुन
                "रिने", "रिे",  # रहने, रहे
                "गनव", "कायव",  # गर्न, कार्य
                "प्रमिमनमध",  # प्रतिनिधि
                "िािािरण",   # वातावरण
                "मममि",     # मिति
                "पमन",      # पनि
                "अमभ",      # अभि
                "जश",       # शि
                "िर्"]


def reason_for(sentence: str):
    if not re.search(r"[ऀ-ॿ]", sentence):
        return "no Devanagari text"
    if len(sentence.split()) < MIN_WORDS_SENT:
        return "too short"
    for name, rx in RULES:
        if rx.search(sentence):
            return name
    for w in KNOWN_BROKEN:
        if w in sentence:
            return f"known broken form: {w}"
    return None


def main():
    chunks = [json.loads(l) for l in (P / "chunks.jsonl").open(encoding="utf-8")]
    clean, rejected = [], []
    tot_words = kept_words = 0
    for c in chunks:
        sents = [s.strip() for s in re.split(r"।", c["text"]) if s.strip()]
        good = []
        for s in sents:
            n = len(s.split())
            tot_words += n
            r = reason_for(s)
            if r:
                rejected.append({"chunk_id": c["chunk_id"], "page": c["page"], "article": c["article"],
                                 "reason": r, "text": s})
            else:
                good.append(s + " ।")
                kept_words += n
        text = " ".join(good)
        if len(text.split()) >= MIN_WORDS_CHUNK:
            clean.append({**c, "text": text, "n_sentences_kept": len(good), "n_sentences_total": len(sents)})
        elif good:
            for s in good:
                rejected.append({"chunk_id": c["chunk_id"], "page": c["page"], "article": c["article"],
                                 "reason": "clean, but chunk too small after filtering", "text": s})
            kept_words -= sum(len(s.split()) for s in good)

    for name, rows in [("chunks_clean.jsonl", clean), ("chunks_rejected.jsonl", rejected)]:
        with (P / name).open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # report
    from collections import Counter
    pages = sum(1 for _ in (P / "pages.jsonl").open(encoding="utf-8"))
    base = (ROOT / "baseline-qa.md").read_text(encoding="utf-8")
    quotes = re.findall(r'\*\*Evidence from text:\*\*\s*"(.+?)"', base)
    clean_text = " ".join(c["text"] for c in clean)
    lines = [
        f"pages processed:           {pages}",
        f"chunks extracted:          {len(chunks)}",
        f"chunks retained (clean):   {len(clean)}",
        f"chunks with nothing usable:{len(chunks) - len(clean)}",
        f"sentences rejected:        {len(rejected)}",
        f"usable text retained:      {100 * kept_words / max(tot_words, 1):.1f}% of words",
        "rejected sentences by reason:",
        *[f"  {k}: {v}" for k, v in Counter(r['reason'] for r in rejected).most_common()],
        "baseline evidence quotes in retained text:",
        *[("  FOUND   " if " ".join(q.split()) in clean_text else "  MISSING ") + q[:60] for q in quotes],
    ]
    report = "\n".join(lines)
    (P / "validation_report.txt").write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
