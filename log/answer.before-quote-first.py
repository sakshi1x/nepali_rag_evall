"""Step 4: answer 30 selected questions with BGE-M3 top-5 chunks, write the human labeling sheet.

Usage:  python src/answer.py --dry-run   (shows the 30 picked questions + cost estimate, calls nothing)
        python src/answer.py --model claude-sonnet-5-5   (needs ANTHROPIC_API_KEY; default model = ANSWER_MODEL or QA_MODEL in .env)
Inputs : results/retrieval_per_question.csv (saved BGE-M3 top-5 from Step 3; nothing is re-encoded,
         chunk text and vectors are not touched), data/ocr/chunks_ocr.jsonl, data/qa/qa_filtered.jsonl, baseline-qa.md
Output : results/labeling.csv  (human_label and human_note are left EMPTY for the human)

Selection (fixed, seed 42): the 5 baseline questions + 25 from the kept set:
5 per type group (number, negation, list, why/how, fact), including 5 questions where BGE-M3 missed the gold chunk.
"why/how", "how" and "why" count as one group. "date" (4 questions) is not in the requested groups, so it is left out.
"""
import argparse, csv, json, os, random, re
from pathlib import Path
from llm import chat, ROOT

PROMPT_VERSION = "ans-v1"
SEED, PER_GROUP, N_MISSES = 42, 5, 5
GROUPS = {"number": "number", "negation": "negation", "list": "list", "fact": "fact",
          "why/how": "why/how", "how": "why/how", "why": "why/how"}
NOT_FOUND = "not found"
OUT = ROOT / "results/labeling.csv"

PROMPT = """Answer the question using ONLY the context passages below (from the Constitution of Nepal).
- Answer in Nepali (Devanagari), short: one sentence or a short list.
- Do not use any outside knowledge.
- If the answer is not in the passages, reply exactly: not found

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def load_baseline():
    md = (ROOT / "baseline-qa.md").read_text(encoding="utf-8")
    out = {}
    for i, block in enumerate(re.split(r"^### ", md, flags=re.M)[1:], 1):
        g = lambda pat: re.search(pat, block).group(1).strip()
        out[f"base{i}"] = dict(question=g(r"\*\*Question:\*\*\s*(.+)"), answer=g(r"\*\*Answer:\*\*\s*(.+)"),
                               evidence=g(r"\*\*Evidence[^*]*\*\*\s*\"(.+?)\""), type=g(r"\*\*Type:\*\*\s*(.+)"))
    return out


def select():
    rows = [r for r in csv.DictReader((ROOT / "results/retrieval_per_question.csv").open(encoding="utf-8"))
            if r["method"] == "bge-m3"]
    qa = {r["qid"]: r for r in map(json.loads, (ROOT / "data/qa/qa_filtered.jsonl").open(encoding="utf-8"))}
    base = load_baseline()
    rnd = random.Random(SEED)
    pool = [r for r in rows if r["baseline"] == "False" and GROUPS.get(r["type"])]
    misses = sorted(rnd.sample([r for r in pool if r["rank"] == "0"], N_MISSES), key=lambda r: r["qid"])
    picked = list(misses)
    for g in ["number", "negation", "list", "why/how", "fact"]:
        need = PER_GROUP - sum(GROUPS[r["type"]] == g for r in picked)
        hits = sorted([r for r in pool if GROUPS[r["type"]] == g and r["rank"] != "0"], key=lambda r: r["qid"])
        picked += rnd.sample(hits, max(need, 0))
    picked = [r for r in rows if r["baseline"] == "True"] + sorted(picked, key=lambda r: r["qid"])
    items = []
    for r in picked:
        src = base[r["qid"]] if r["baseline"] == "True" else qa[r["qid"]]
        items.append(dict(question_id=r["qid"], type=src["type"], question=src["question"],
                          reference_answer=src["answer"], evidence=src["evidence"],
                          retrieved_chunk_ids=" ".join(t.split(":")[0] for t in r["top5"].split()),
                          gold_rank=r["rank"]))
    return items


def build_prompt(item, chunks):
    ctx = "\n\n".join(f"[{i}] (chunk {cid})\n{chunks[cid]}"
                      for i, cid in enumerate(item["retrieved_chunk_ids"].split(), 1))
    return PROMPT.format(context=ctx, question=item["question"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", help="e.g. claude-sonnet-5-5 or claude-haiku-5-5")
    args = ap.parse_args()
    chunks = {c["chunk_id"]: c["text"] for c in map(json.loads, (ROOT / "data/ocr/chunks_ocr.jsonl").open(encoding="utf-8"))}
    items = select()
    assert len(items) == 30, len(items)
    prompts = [build_prompt(it, chunks) for it in items]

    if args.dry_run:
        from collections import Counter
        print("picked:", len(items), "| by type:", dict(Counter(GROUPS.get(i["type"], i["type"]) for i in items)),
              "| BGE-M3 misses:", sum(i["gold_rank"] == "0" for i in items))
        for it in items:
            print(f"  {it['question_id']:6} {it['type']:9} rank {it['gold_rank']}  {it['question'][:70]}")
        chars = sum(map(len, prompts))
        print(f"calls: {len(prompts)} | prompt chars: {chars:,}")
        return

    model = args.model or os.environ.get("ANSWER_MODEL") or os.environ["QA_MODEL"]
    print(f"model: {model} | prompt: {PROMPT_VERSION}")
    for it, p in zip(items, prompts):
        it["rag_answer"] = chat(model, [{"role": "user", "content": p}]).strip()
        it["human_label"], it["human_note"] = "", ""
        print(f"{it['question_id']}: {it['rag_answer'][:80]}")
    cols = ["question_id", "type", "question", "reference_answer", "evidence", "rag_answer",
            "retrieved_chunk_ids", "gold_rank", "human_label", "human_note"]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig so Excel shows Nepali correctly
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({c: it[c] for c in cols} for it in items)
    nf = sum(it["rag_answer"].lower().startswith(NOT_FOUND) for it in items)
    print(f"\nwrote {OUT} | {len(items)} rows | 'not found' answers: {nf} | human_label left empty")


if __name__ == "__main__":
    main()
