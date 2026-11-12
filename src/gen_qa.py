"""Step 2a: generate Nepali Q&A pairs from random chunks.
Usage:  python src/gen_qa.py --dry-run     (prints number of calls + rough token estimate, calls nothing)
        python src/gen_qa.py               (needs QA_MODEL and ANTHROPIC_API_KEY in .env)
Output: data/qa/qa_generated.jsonl"""
import argparse, json, os, random, re
from pathlib import Path
from llm import chat, ROOT

PROMPT_VERSION = "gen-v1"
N_CHUNKS, SEED = 60, 42
CHUNKS = ROOT / "data/ocr/chunks_ocr.jsonl"  # directive-v3: OCR chunks, not the corrupted v1 text
OUT = ROOT / "data/qa/qa_generated.jsonl"

PROMPT = """तल नेपालको संविधानको एउटा अंश छ। यसबाट २ देखि ३ वटा प्रश्न-उत्तर बनाउनुहोस्।

Rules:
- Questions and answers in Nepali (Devanagari).
- Use different types where the text allows: fact, number, date, list, negation, why/how.
- Phrase questions the way a real person would ask. Do NOT start with "नेपालको संविधान अनुसार".
- No yes/no questions.
- "evidence" must be copied EXACTLY, character for character, from the text below (one sentence or clause).
- The answer must be short and fully supported by the evidence.
- Return ONLY a JSON list: [{{"question": "...", "answer": "...", "evidence": "...", "type": "..."}}]

TEXT:
{text}"""


def parse_json_list(raw: str):
    m = re.search(r"\[.*\]", raw, re.S)
    return json.loads(m.group(0)) if m else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    chunks = [json.loads(l) for l in CHUNKS.open(encoding="utf-8")]
    usable = [c for c in chunks if len(c["text"].split()) >= 40]
    random.seed(SEED)
    picked = random.sample(usable, min(N_CHUNKS, len(usable)))

    if args.dry_run:
        chars = sum(len(PROMPT) + len(c["text"]) for c in picked)
        print(f"calls: {len(picked)}  input chars: {chars:,}  (Devanagari is roughly 1 token per 1-2 chars,"
              f" so about {chars//2:,}-{chars:,} input tokens + ~{len(picked)*400:,} output tokens)")
        return

    model = os.environ["QA_MODEL"]
    n_ok = n_bad = 0
    with OUT.open("w", encoding="utf-8") as f:
        for c in picked:
            raw = chat(model, [{"role": "user", "content": PROMPT.format(text=c["text"])}])
            try:
                items = parse_json_list(raw)
            except json.JSONDecodeError:
                items, n_bad = [], n_bad + 1
            for it in items:
                it.update(gold_chunk_id=c["chunk_id"], model=model, prompt_version=PROMPT_VERSION)
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                n_ok += 1
    print(f"generated: {n_ok} pairs from {len(picked)} chunks, unparseable responses: {n_bad} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
