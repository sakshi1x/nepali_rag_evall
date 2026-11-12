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


# Step 6 fix (ans-v2, "quote first, then answer"): the model must copy the one sentence that directly answers the
# question, word for word, before answering. A code check then verifies the quote is really in the retrieved chunks;
# if it is not (or no quote is given), the answer is forced to "not found".
PROMPT_V2 = """Answer the question using ONLY the context passages below (from the Constitution of Nepal).

Step 1: Find the ONE sentence in the passages that directly answers THIS question (same subject, same thing asked).
Copy it exactly, character for character. A sentence about a related but different subject does NOT count.
Step 2: Answer in Nepali (Devanagari), short, using only that sentence.
If no sentence directly answers the question, use an empty quote and the answer "not found".

Return ONLY JSON: {{"quote": "<exact sentence or empty>", "answer": "<short Nepali answer or not found>"}}

CONTEXT:
{context}

QUESTION: {question}"""


def norm_q(s):
    import unicodedata
    s = unicodedata.normalize("NFC", s or "").replace("\u200c", "").replace("\u200d", "")
    return " ".join(re.sub(r"[।॥,;:!?\"'“”‘’()\[\]\-–—.]", " ", s).split())


def quote_match(quote, ctx):
    """1.0 = exact. Otherwise the share of quote characters found in order in the context (tolerates small OCR
    spelling fixes the model makes when copying, e.g. सार्वभीम -> सार्वभौम). Scattered matches score low."""
    import difflib
    q = norm_q(quote)
    if not q:
        return 0.0
    if q in ctx:
        return 1.0
    sm = difflib.SequenceMatcher(None, ctx, q, autojunk=False)
    i, j, k = sm.find_longest_match(0, len(ctx), 0, len(q))
    start = max(0, i - j - 20)
    win = ctx[start:start + len(q) + 40]
    return round(sum(b.size for b in difflib.SequenceMatcher(None, win, q, autojunk=False).get_matching_blocks()) / len(q), 3)


QUOTE_MIN = 0.9  # below this the quote is treated as not in the chunks


def parse_v2(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    return str(d.get("quote", "")).strip(), str(d.get("answer", "")).strip(), bool(d)


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


def build_prompt(item, chunks, template=None):
    ctx = "\n\n".join(f"[{i}] (chunk {cid})\n{chunks[cid]}"
                      for i, cid in enumerate(item["retrieved_chunk_ids"].split(), 1))
    return (template or PROMPT).format(context=ctx, question=item["question"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", help="e.g. claude-sonnet-5-5 or claude-haiku-5-5")
    ap.add_argument("--hybrid-only", help="Step 6 fix 2: comma-separated question ids; answer them (prompt ans-v1) "
                    "with the hybrid-rrf top 5 instead of BGE-M3 -> results/labeling_hybrid.csv")
    ap.add_argument("--quote-first", action="store_true", help="Step 6 fix: prompt ans-v2 + quote check -> results/labeling_v2.csv")
    args = ap.parse_args()
    chunks = {c["chunk_id"]: c["text"] for c in map(json.loads, (ROOT / "data/ocr/chunks_ocr.jsonl").open(encoding="utf-8"))}
    items = select()
    assert len(items) == 30, len(items)
    if args.hybrid_only:
        keep = args.hybrid_only.split(",")
        hyb = {r["qid"]: r for r in csv.DictReader((ROOT / "results/retrieval_per_question.csv").open(encoding="utf-8"))
               if r["method"] == "hybrid-rrf"}
        v1 = {r["question_id"]: r for r in csv.DictReader((ROOT / "results/labeling_human.csv").open(encoding="utf-8-sig"))}
        items = [dict(it, retrieved_chunk_ids=" ".join(t.split(":")[0] for t in hyb[it["question_id"]]["top5"].split()),
                      gold_rank=hyb[it["question_id"]]["rank"], gold_rank_v1=it["gold_rank"],
                      rag_answer_v1=v1[it["question_id"]]["rag_answer"], human_label_v1=v1[it["question_id"]]["human_label"])
                 for it in items if it["question_id"] in keep]
        assert len(items) == len(keep), "unknown question id"
    prompts = [build_prompt(it, chunks, PROMPT_V2 if args.quote_first else None) for it in items]

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
    if args.quote_first:
        return run_v2(items, prompts, chunks, model)
    print(f"model: {model} | prompt: {PROMPT_VERSION}")
    for it, p in zip(items, prompts):
        it["rag_answer"] = chat(model, [{"role": "user", "content": p}]).strip()
        it["human_label"], it["human_note"] = "", ""
        print(f"{it['question_id']}: {it['rag_answer'][:80]}")
    cols = ["question_id", "type", "question", "reference_answer", "evidence", "rag_answer",
            "retrieved_chunk_ids", "gold_rank", "human_label", "human_note"]
    out = OUT
    if args.hybrid_only:
        cols = cols[:7] + ["gold_rank", "gold_rank_v1", "rag_answer_v1", "human_label_v1", "human_label", "human_note"]
        out = ROOT / "results/labeling_hybrid.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig so Excel shows Nepali correctly
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({c: it[c] for c in cols} for it in items)
    nf = sum(it["rag_answer"].lower().startswith(NOT_FOUND) for it in items)
    print(f"\nwrote {out} | {len(items)} rows | 'not found' answers: {nf} | human_label left empty")


def run_v2(items, prompts, chunks, model):
    """Same 30 questions, same saved top-5 chunks, same model; only the prompt changes (+ quote check)."""
    v1 = {r["question_id"]: r for r in csv.DictReader((ROOT / "results/labeling_human.csv").open(encoding="utf-8-sig"))}
    print(f"model: {model} | prompt: ans-v2 (quote-first)")
    bad_json = 0
    for it, p in zip(items, prompts):
        quote, answer, ok = parse_v2(chat(model, [{"role": "user", "content": p}]))
        bad_json += not ok
        ctx = norm_q(" ".join(chunks[c] for c in it["retrieved_chunk_ids"].split()))
        score = quote_match(quote, ctx)
        found = score >= QUOTE_MIN
        if not found or not answer:
            answer = NOT_FOUND
        status = ("exact" if score == 1.0 else f"near {score}") if found else ("no quote" if not quote else f"NOT FOUND ({score}) -> forced not found")
        it.update(quote=quote, quote_in_chunks=status,
                  rag_answer=answer, rag_answer_v1=v1[it["question_id"]]["rag_answer"],
                  human_label_v1=v1[it["question_id"]]["human_label"], human_label="", human_note="")
        print(f"{it['question_id']}: [{it['quote_in_chunks']}] {answer[:70]}")
    cols = ["question_id", "type", "question", "reference_answer", "evidence", "quote", "quote_in_chunks", "rag_answer",
            "rag_answer_v1", "human_label_v1", "retrieved_chunk_ids", "gold_rank", "human_label", "human_note"]
    out = ROOT / "results/labeling_v2.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({c: it[c] for c in cols} for it in items)
    nf = [it["question_id"] for it in items if it["rag_answer"].lower().startswith(NOT_FOUND)]
    misses = [it["question_id"] for it in items if it["gold_rank"] == "0"]
    print(f"\nwrote {out} | not found: {len(nf)} {nf} | retrieval misses now not found: "
          f"{sum(q in nf for q in misses)}/{len(misses)} | quote failed check: "
          f"{sum(it['quote_in_chunks'].startswith('NOT') for it in items)} | invalid JSON: {bad_json} | human_label left empty")


if __name__ == "__main__":
    main()
