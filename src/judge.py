"""Step 5: two LLM judges vs the human labels.

Usage:  python src/judge.py --selftest     (checks the kappa function on a tiny hand-worked example, no API)
        python src/judge.py --dry-run      (counts calls + prompt size, no API)
        python src/judge.py                (needs ANTHROPIC_API_KEY)
Input : results/labeling_human.csv (human labels, never changed by this script)
Output: results/judge_verdicts.csv, results/judge_metrics.csv, results/disagreements.csv

Label rule (human decision, Entry #20): human "not found" counts as "wrong" (the answer did not give the fact).
Judges: two different Claude models, neither of them the answer model (claude-sonnet-5-5).
"""
import argparse, csv, json, re
from collections import Counter
from llm import chat, ROOT

PROMPT_VERSION = "judge-v1"
JUDGES = ["claude-opus-5-5", "claude-haiku-5-5"]
IN = ROOT / "results/labeling_human.csv"
LABEL_MAP = {"correct": "correct", "wrong": "wrong", "not found": "wrong"}

PROMPT = """You are grading an answer from a question-answering system about the Constitution of Nepal.

QUESTION: {question}
REFERENCE ANSWER: {reference_answer}
EVIDENCE (exact text from the Constitution): {evidence}
SYSTEM ANSWER: {rag_answer}

Grade the SYSTEM ANSWER:
- "correct" if it states the same fact as the reference answer (wording may differ) and adds nothing false.
- "wrong" if the key fact is missing, different, or contradicted, if it adds a false claim, or if it says "not found".

Return ONLY JSON: {{"verdict": "correct" or "wrong", "reason": "one short sentence"}}"""


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] / n * cb[k] / n for k in set(a) | set(b))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def selftest():
    # By hand: agreement 3/4 = 0.75; chance = 0.5*0.25 (correct) + 0.5*0.75 (wrong) = 0.5; kappa = (0.75-0.5)/(1-0.5) = 0.5
    k = kappa(["correct", "correct", "wrong", "wrong"], ["correct", "wrong", "wrong", "wrong"])
    assert abs(k - 0.5) < 1e-9, k
    assert kappa(["correct", "wrong"], ["correct", "wrong"]) == 1.0
    print("kappa self-test OK: hand example = 0.5, perfect agreement = 1.0")


def parse(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        d = None
    if d and str(d.get("verdict", "")).strip().lower() in ("correct", "wrong"):
        return d["verdict"].strip().lower(), str(d.get("reason", "")).strip()
    return None, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    selftest()
    if args.selftest:
        return
    rows = list(csv.DictReader(IN.open(encoding="utf-8-sig")))
    bad = [r["question_id"] for r in rows if r["human_label"].strip().lower() not in LABEL_MAP]
    assert not bad, f"unknown human labels: {bad}"
    human = {r["question_id"]: LABEL_MAP[r["human_label"].strip().lower()] for r in rows}
    print(f"rows {len(rows)} | human (after not found -> wrong): {dict(Counter(human.values()))}")
    prompts = {r["question_id"]: PROMPT.format(**{k: r[k] for k in ["question", "reference_answer", "evidence", "rag_answer"]})
               for r in rows}
    if args.dry_run:
        print(f"judges {JUDGES} | calls {len(JUDGES) * len(rows)} | prompt chars per judge {sum(map(len, prompts.values())):,}")
        return

    verdicts, metrics, disagree, invalid = [], [], [], Counter()
    for model in JUDGES:
        print(f"\n== {model} ({PROMPT_VERSION}) ==")
        for r in rows:
            qid = r["question_id"]
            msgs = [{"role": "user", "content": prompts[qid]}]
            v, reason = parse(chat(model, msgs))
            if v is None:  # one retry, counted
                invalid[model] += 1
                msgs += [{"role": "assistant", "content": reason},
                         {"role": "user", "content": 'Reply with ONLY the JSON object {"verdict": "correct" or "wrong", "reason": "..."}.'}]
                v, reason = parse(chat(model, msgs))
                assert v, f"{model} {qid}: still invalid JSON after retry: {reason[:200]}"
            verdicts.append(dict(question_id=qid, judge=model, human_label=human[qid], judge_verdict=v, judge_reason=reason))
            if v != human[qid]:
                disagree.append(dict(question_id=qid, judge=model, question=r["question"], reference_answer=r["reference_answer"],
                                     rag_answer=r["rag_answer"], human_label=r["human_label"], judge_verdict=v,
                                     judge_reason=reason, failure_type=""))
            print(f"{qid}: human {human[qid]:7} judge {v:7} {'' if v == human[qid] else '<- DISAGREE'}")
        h = [human[r["question_id"]] for r in rows]
        j = [x["judge_verdict"] for x in verdicts if x["judge"] == model]
        n_wrong = h.count("wrong")
        fp = sum(hh == "wrong" and jj == "correct" for hh, jj in zip(h, j))
        fn = sum(hh == "correct" and jj == "wrong" for hh, jj in zip(h, j))
        metrics.append(dict(judge=model, prompt=PROMPT_VERSION, n=len(h), agreement=round(sum(a == b for a, b in zip(h, j)) / len(h), 3),
                            cohen_kappa=round(kappa(h, j), 3), false_positive_rate=round(fp / n_wrong, 3) if n_wrong else "n/a",
                            false_positives=fp, false_negatives=fn, human_wrong=n_wrong, invalid_json_retried=invalid[model]))

    out = ROOT / "results"
    for name, data in [("judge_verdicts.csv", verdicts), ("judge_metrics.csv", metrics), ("disagreements.csv", disagree)]:
        with (out / name).open("w", encoding="utf-8-sig", newline="") as f:
            cols = list(data[0].keys()) if data else ["question_id", "judge", "human_label", "judge_verdict", "judge_reason", "failure_type"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(data)
    print("\njudge             agree  kappa  FP-rate  FP  FN  invalidJSON")
    for m in metrics:
        print(f"{m['judge']:17} {m['agreement']:.3f}  {m['cohen_kappa']:.3f}  {m['false_positive_rate']}  {m['false_positives']}  {m['false_negatives']}  {m['invalid_json_retried']}")
    print(f"disagreements: {len(disagree)} rows -> results/disagreements.csv")


if __name__ == "__main__":
    main()
