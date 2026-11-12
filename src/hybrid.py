"""Step 6, fix 2: hybrid retrieval = Reciprocal Rank Fusion (RRF) of the saved BM25 and BGE-M3 top-5 lists.

Usage: python src/hybrid.py
Input : results/retrieval_per_question.csv (Step 3 output; nothing is re-encoded, no API calls)
Output: rows with method "hybrid-rrf" added to results/retrieval_per_question.csv,
        results/retrieval_metrics_hybrid.csv, results/fix2_before_after.csv

RRF score of a chunk = sum over methods of 1 / (K + rank), K = 60 (standard value). Ties: BGE-M3's order first.
A question counts as found if one of the fused top 5 is a gold chunk (same gold rule as Step 3).
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
K, TOP = 60, 5
P = ROOT / "results/retrieval_per_question.csv"


def main():
    rows = [r for r in csv.DictReader(P.open(encoding="utf-8")) if r["method"] != "hybrid-rrf"]
    by = {(r["method"], r["qid"]): r for r in rows}
    fused = []
    for r in [x for x in rows if x["method"] == "bge-m3"]:
        score, order = defaultdict(float), {}
        for m in ["bge-m3", "bm25"]:
            for i, t in enumerate(by[(m, r["qid"])]["top5"].split(), 1):
                cid = t.split(":")[0]
                score[cid] += 1 / (K + i)
                order.setdefault(cid, (0 if m == "bge-m3" else 1, i))
        top = sorted(score, key=lambda c: (-score[c], order[c]))[:TOP]
        gold = set(r["gold_chunks"].split())
        rank = next((i for i, c in enumerate(top, 1) if c in gold), 0)
        fused.append({**r, "method": "hybrid-rrf", "top5": " ".join(f"{c}:{score[c]:.4f}" for c in top),
                      "rank": rank, "hit_at_5": int(rank > 0), "rr": round(1 / rank, 4) if rank else 0})
    with P.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows + fused)

    allr = rows + fused
    def metric(m, keep):
        rs = [r for r in allr if r["method"] == m and keep(r)]
        return len(rs), sum(int(r["hit_at_5"]) for r in rs) / len(rs), sum(float(r["rr"]) for r in rs) / len(rs)
    met = []
    types = sorted({r["type"] for r in allr if r["baseline"] == "False"})
    for m in ["bm25", "bge-m3", "hybrid-rrf"]:
        for t in ["ALL"] + types:
            n, rec, mrr = metric(m, lambda r: r["baseline"] == "False" and (t == "ALL" or r["type"] == t))
            met.append(dict(method=m, type=t, n=n, recall_at_5=round(rec, 3), mrr=round(mrr, 3)))
    with (ROOT / "results/retrieval_metrics_hybrid.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(met[0].keys())); w.writeheader(); w.writerows(met)

    gen = lambda m: metric(m, lambda r: r["baseline"] == "False")
    base = lambda m: sum(1 for r in allr if r["method"] == m and r["baseline"] == "True" and str(r["rank"]) == "1")
    miss = lambda m: [r["qid"] for r in allr if r["method"] == m and r["baseline"] == "False" and str(r["rank"]) == "0"]
    (_, rb, mb), (_, rh, mh) = gen("bge-m3")[0:3], gen("hybrid-rrf")[0:3]
    out = [("Recall@5 (177 generated questions)", round(rb, 3), round(rh, 3)),
           ("MRR (177 generated questions)", round(mb, 3), round(mh, 3)),
           ("misses (gold not in top 5)", len(miss("bge-m3")), len(miss("hybrid-rrf"))),
           ("baseline questions with gold at rank 1 (of 5)", base("bge-m3"), base("hybrid-rrf"))]
    with (ROOT / "results/fix2_before_after.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["metric", "before (BGE-M3 only)", "after (hybrid RRF)", "change"])
        for m_, b, a in out: w.writerow([m_, b, a, round(a - b, 3)])
    for m_, b, a in out: print(f"{m_:48} {b:>7} -> {a}")
    print("BGE-M3 misses:", miss("bge-m3"), "| hybrid misses:", miss("hybrid-rrf"), "| BM25 misses:", miss("bm25"))
    print("\n30 labeling questions whose top 5 changes:")
    lab = [r["question_id"] for r in csv.DictReader((ROOT / "results/labeling.csv").open(encoding="utf-8-sig"))]
    f_by = {r["qid"]: r for r in fused}
    for q in lab:
        old = [t.split(":")[0] for t in by[("bge-m3", q)]["top5"].split()]
        new = [t.split(":")[0] for t in f_by[q]["top5"].split()]
        if old != new:
            print(f"  {q}: gold rank {by[('bge-m3', q)]['rank']} -> {f_by[q]['rank']}  (set changed: {set(old) != set(new)})")


if __name__ == "__main__":
    main()
