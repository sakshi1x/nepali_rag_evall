"""Step 2b: filter generated Q&A. Every rejected row keeps a reason.
Output: data/qa/qa_filtered.jsonl, data/qa/qa_rejected.jsonl"""
import json, random, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
chunks = {c["chunk_id"]: c for c in map(json.loads, (ROOT / "data/ocr/chunks_ocr.jsonl").open(encoding="utf-8"))}
rows = [json.loads(l) for l in (ROOT / "data/qa/qa_generated.jsonl").open(encoding="utf-8")]


def norm(s):
    return " ".join(re.sub(r"[।,;:\"'“”‘’()\-–]", " ", s or "").split())


def grams(s, n=3):
    s = norm(s)
    return {s[i:i + n] for i in range(max(len(s) - n + 1, 1))}


YESNO = re.compile(r"(हो\s*कि\s*होइन|छ\s*कि\s*छैन|हुन्छ\s*कि\s*हुँदैन)")

kept, rejected, seen = [], [], []
for r in rows:
    q, a, ev = r.get("question", ""), r.get("answer", ""), r.get("evidence", "")
    chunk_text = norm(chunks[r["gold_chunk_id"]]["text"])
    reason = None
    if not q or not a or not ev:
        reason = "missing field"
    elif norm(ev) not in chunk_text:
        reason = "evidence not found in chunk"
    elif not any(w in norm(ev) for w in norm(a).split() if len(w) > 1):
        reason = "answer not supported by evidence"
    elif len(a.split()) > 25:
        reason = "answer too long"
    elif YESNO.search(q):
        reason = "yes/no question"
    else:
        g = grams(q)
        if any(len(g & s) / max(len(g | s), 1) > 0.8 for s in seen):
            reason = "near-duplicate question"
        else:
            seen.append(g)
    (rejected if reason else kept).append({**r, **({"reject_reason": reason} if reason else {})})

for name, data in [("qa_filtered.jsonl", kept), ("qa_rejected.jsonl", rejected)]:
    with (ROOT / "data/qa" / name).open("w", encoding="utf-8") as f:
        for i, r in enumerate(data):
            if name == "qa_filtered.jsonl":
                r["qid"] = f"q{i:03d}"
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"generated {len(rows)} | kept {len(kept)} | rejected {len(rejected)}")
print("rejected by reason:", dict(collections.Counter(r["reject_reason"] for r in rejected)))
print("kept by type:", dict(collections.Counter(r.get("type") for r in kept)))
random.seed(42)
print("\n--- 10 random kept pairs: spot-check these yourself ---")
for r in random.sample(kept, min(10, len(kept))):
    print(f"\n[{r['qid']}] ({r.get('type')}) {r['question']}\n  A: {r['answer']}\n  E: {r['evidence'][:120]}")
