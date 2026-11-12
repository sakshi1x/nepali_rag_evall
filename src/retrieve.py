"""Step 3: retrieval, BM25 vs BGE-M3. Reports Recall@5 and MRR (overall and by question type).

Usage:
  python src/retrieve.py --method bm25     # fast, no download
  python src/retrieve.py --method bge      # downloads BAAI/bge-m3 (~2 GB) the first time, slow on CPU
  python src/retrieve.py --method both

Inputs : data/ocr/chunks_ocr.jsonl, data/qa/qa_filtered.jsonl, baseline-qa.md
Outputs: results/retrieval_per_question.csv, results/retrieval_metrics.csv, results/baseline_top1.txt
         data/chroma/ (saved BGE-M3 vectors, reused on later runs)

Gold: a question counts as found if a retrieved chunk is its gold_chunk_id OR any other chunk whose
text contains the full evidence sentence (chunks overlap by 50 words, so the same sentence can sit in 2 chunks).
"""
import argparse, csv, json, re, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
K = 5
RESULTS = ROOT / "results"
PUNCT = re.compile(r"[।॥,;:!?\"'“”‘’()\[\]{}\-–—/.]")


def norm(s):
    s = unicodedata.normalize("NFC", s or "").replace("‌", "").replace("‍", "")
    return " ".join(PUNCT.sub(" ", s).split())


def tokenize(s):
    return norm(s).split()


def load():
    chunks = [json.loads(l) for l in (ROOT / "data/ocr/chunks_ocr.jsonl").open(encoding="utf-8")]
    qs = [json.loads(l) for l in (ROOT / "data/qa/qa_filtered.jsonl").open(encoding="utf-8")]
    normed = {c["chunk_id"]: norm(c["text"]) for c in chunks}

    def gold_set(evidence, gold_id=None):
        ev = norm(evidence)
        g = {cid for cid, t in normed.items() if ev and ev in t}
        if gold_id:
            g.add(gold_id)
        return g

    rows = [dict(qid=q["qid"], type=q.get("type", ""), question=q["question"],
                 gold=gold_set(q["evidence"], q["gold_chunk_id"]), baseline=False) for q in qs]
    md = (ROOT / "baseline-qa.md").read_text(encoding="utf-8")
    for i, block in enumerate(re.split(r"^### ", md, flags=re.M)[1:], 1):
        q = re.search(r"\*\*Question:\*\*\s*(.+)", block).group(1).strip()
        ev = re.search(r"\*\*Evidence[^*]*\*\*\s*\"(.+?)\"", block).group(1).strip()
        t = re.search(r"\*\*Type:\*\*\s*(.+)", block).group(1).strip()
        rows.append(dict(qid=f"base{i}", type=t, question=q, gold=gold_set(ev), baseline=True))
    return chunks, rows


def bm25_search(chunks, rows):
    from rank_bm25 import BM25Okapi
    bm = BM25Okapi([tokenize(c["text"]) for c in chunks])
    out = {}
    for r in rows:
        scores = bm.get_scores(tokenize(r["question"]))
        top = sorted(range(len(chunks)), key=lambda i: -scores[i])[:K]
        out[r["qid"]] = [(chunks[i]["chunk_id"], float(scores[i])) for i in top]
    return out


def bge_search(chunks, rows):
    import chromadb
    from sentence_transformers import SentenceTransformer
    print("Loading BAAI/bge-m3 (first run downloads ~2 GB; encoding on CPU can take 10+ minutes)...")
    model = SentenceTransformer("BAAI/bge-m3")
    model.max_seq_length = 1024
    client = chromadb.PersistentClient(path=str(ROOT / "data/chroma"))
    col = client.get_or_create_collection("chunks_bge_m3", metadata={"hnsw:space": "cosine"})
    ids = [c["chunk_id"] for c in chunks]
    if col.count() != len(ids) or set(col.get(ids=ids)["ids"]) != set(ids):
        print(f"Encoding {len(ids)} chunks...")
        client.delete_collection("chunks_bge_m3")
        col = client.create_collection("chunks_bge_m3", metadata={"hnsw:space": "cosine"})
        texts = [norm(c["text"]) for c in chunks]
        emb = model.encode(texts, batch_size=4, normalize_embeddings=True, show_progress_bar=True)
        col.add(ids=ids, embeddings=emb.tolist(), metadatas=[{"page": c["page"]} for c in chunks])
    else:
        print("Reusing saved chunk vectors in data/chroma")
    qemb = model.encode([norm(r["question"]) for r in rows], batch_size=16,
                        normalize_embeddings=True, show_progress_bar=True)
    res = col.query(query_embeddings=qemb.tolist(), n_results=K)
    return {r["qid"]: [(cid, 1 - d) for cid, d in zip(res["ids"][i], res["distances"][i])]
            for i, r in enumerate(rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["bm25", "bge", "both"], default="both")
    methods = {"bm25": ["bm25"], "bge": ["bge-m3"], "both": ["bm25", "bge-m3"]}[ap.parse_args().method]
    chunks, rows = load()
    text = {c["chunk_id"]: c["text"] for c in chunks}
    RESULTS.mkdir(exist_ok=True)
    per_q_path = RESULTS / "retrieval_per_question.csv"
    old = [r for r in csv.DictReader(per_q_path.open(encoding="utf-8"))] if per_q_path.exists() else []
    old = [r for r in old if r["method"] not in methods]
    new, base_lines = [], []

    for m in methods:
        hits = (bm25_search if m == "bm25" else bge_search)(chunks, rows)
        base_lines.append(f"===== {m} =====")
        for r in rows:
            ranked = [cid for cid, _ in hits[r["qid"]]]
            rank = next((i + 1 for i, cid in enumerate(ranked) if cid in r["gold"]), 0)
            new.append(dict(method=m, qid=r["qid"], type=r["type"], baseline=r["baseline"],
                            question=r["question"], gold_chunks=" ".join(sorted(r["gold"])),
                            top5=" ".join(f"{cid}:{s:.3f}" for cid, s in hits[r["qid"]]),
                            rank=rank, hit_at_5=int(rank > 0), rr=round(1 / rank, 4) if rank else 0))
            if r["baseline"]:
                top1 = ranked[0]
                base_lines.append(f"{r['qid']} | gold {sorted(r['gold']) or 'NOT FOUND IN ANY CHUNK'} | rank {rank or '-'}\n"
                                  f"  Q: {r['question']}\n  top1 {top1}: {text[top1][:160]}")

    allrows = old + new
    with per_q_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(new[0].keys()))
        w.writeheader(); w.writerows(allrows)

    groups = defaultdict(list)
    for r in allrows:
        if str(r["baseline"]) == "True":
            continue
        groups[(r["method"], "ALL")].append(r)
        groups[(r["method"], r["type"])].append(r)
    metrics = []
    for (m, t), rs in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1] != "ALL", x[0][1])):
        rec = sum(int(r["hit_at_5"]) for r in rs) / len(rs)
        mrr = sum(float(r["rr"]) for r in rs) / len(rs)
        assert 0 <= rec <= 1 and 0 <= mrr <= 1
        metrics.append(dict(method=m, type=t, n=len(rs), recall_at_5=round(rec, 3), mrr=round(mrr, 3)))
    with (RESULTS / "retrieval_metrics.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(metrics[0].keys()))
        w.writeheader(); w.writerows(metrics)

    (RESULTS / "baseline_top1.txt").open("a" if old else "w", encoding="utf-8").write("\n".join(base_lines) + "\n")
    print("\n".join(base_lines))
    print("\nmethod  type        n    Recall@5  MRR")
    for x in metrics:
        print(f"{x['method']:7} {x['type']:10} {x['n']:4}   {x['recall_at_5']:.3f}    {x['mrr']:.3f}")


if __name__ == "__main__":
    main()
