"""Step 7: Streamlit page for the Nepali RAG eval.

Shows: document -> questions -> Recall@5/MRR -> judge agreement -> failure examples.
Reads only saved files in data/ and results/. No API calls, no model download, no re-encoding.

Run (from the project folder):  streamlit run src/app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent  # project folder (this file is in src/)
RES = ROOT / "results"


def jsonl(path):
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


@st.cache_data
def csv(name):
    return pd.read_csv(RES / name, encoding="utf-8-sig", dtype=str).fillna("")


@st.cache_data
def load_doc():
    pages = [p for f in sorted((ROOT / "data/ocr").glob("pages_ocr*.jsonl")) for p in jsonl(f)]
    pages = {p["page"]: p["text"] for p in pages}  # one entry per page
    chunks = jsonl(ROOT / "data/ocr/chunks_ocr.jsonl")
    return pages, chunks


@st.cache_data
def load_qa():
    return (jsonl(ROOT / "data/qa/qa_generated.jsonl"), jsonl(ROOT / "data/qa/qa_filtered.jsonl"),
            jsonl(ROOT / "data/qa/qa_rejected.jsonl"))


st.set_page_config(page_title="Nepali RAG Eval", layout="wide")
st.title("Nepali RAG evaluation: Constitution of Nepal")
st.caption("Every number on this page is read from the saved files in data/ and results/.")

# 1. Document ---------------------------------------------------------------
st.header("1. Document")
pages, chunks = load_doc()
words = sum(len(t.split()) for t in pages.values())
c1, c2, c3, c4 = st.columns(4)
c1.metric("Pages (OCR)", len(pages))
c2.metric("Words", f"{words:,}")
c3.metric("Chunks", len(chunks))
c4.metric("Chunks without Article number", sum(bool(c["number_missing_in_ocr"]) for c in chunks))
st.write("The PDF's text layer was corrupted, so every page was read with OCR (Tesseract, Nepali). "
         "Chunks follow Articles (धारा), about 300 words each with 50 words of overlap.")
ids = [c["chunk_id"] for c in chunks]
pick = st.selectbox("Look at a chunk", ids, index=ids.index("o0002") if "o0002" in ids else 0)
ch = chunks[ids.index(pick)]
st.caption(f"page {ch['page']} · Article {ch['article'] or 'number missing in OCR'} · {ch['title']}")
st.text(ch["text"][:1500])

# 2. Questions --------------------------------------------------------------
st.header("2. Questions")
gen, kept, rej = load_qa()
c1, c2, c3 = st.columns(3)
c1.metric("Generated", len(gen))
c2.metric("Kept after filter", len(kept))
c3.metric("Rejected", len(rej))
left, right = st.columns(2)
with left:
    st.write("Kept questions by type")
    st.bar_chart(pd.Series([q["type"] for q in kept]).value_counts())
with right:
    st.write("Rejected, with reason")
    st.dataframe(pd.DataFrame(rej)[["question", "reject_reason"]], hide_index=True)
st.write("Sample of kept questions")
st.dataframe(pd.DataFrame(kept)[["qid", "type", "question", "answer", "gold_chunk_id"]].head(10), hide_index=True)

# 3. Retrieval --------------------------------------------------------------
st.header("3. Retrieval: Recall@5 and MRR")
ret = csv("retrieval_metrics_hybrid.csv")
for col in ["n", "recall_at_5", "mrr"]:
    ret[col] = pd.to_numeric(ret[col])
overall = ret[ret["type"] == "ALL"].set_index("method")[["recall_at_5", "mrr"]]
cols = st.columns(len(overall))
for col, (m, row) in zip(cols, overall.iterrows()):
    col.metric(f"{m}: Recall@5", f"{row.recall_at_5:.3f}")
    col.metric(f"{m}: MRR", f"{row.mrr:.3f}")
st.bar_chart(overall, stack=False)
st.caption(f"{int(ret[ret.type == 'ALL'].n.iloc[0])} generated questions. "
           "hybrid-rrf = Step 6 fix: Reciprocal Rank Fusion of the saved BM25 and BGE-M3 top 5.")
with st.expander("By question type"):
    st.dataframe(ret[ret["type"] != "ALL"].pivot(index="type", columns="method", values="recall_at_5"))
with st.expander("5 hand-written baseline questions (top-1 chunk)"):
    st.text((RES / "baseline_top1.txt").read_text(encoding="utf-8"))

# 4. Judges -----------------------------------------------------------------
st.header("4. LLM judges vs human labels")
jm = csv("judge_metrics.csv")
for col in ["agreement", "cohen_kappa"]:
    jm[col] = pd.to_numeric(jm[col])
st.bar_chart(jm.set_index("judge")[["agreement", "cohen_kappa"]], stack=False)
st.dataframe(jm, hide_index=True)
human = csv("labeling_human.csv")
st.caption(f"{len(human)} answers labeled by hand: "
           + ", ".join(f"{v} {k}" for k, v in human["human_label"].value_counts().items())
           + ". For the judges, \"not found\" counts as wrong.")
jv = csv("judge_verdicts.csv")
st.write("Human label (rows) vs judge verdict (columns)")
st.dataframe(pd.crosstab([jv["judge"], jv["human_label"]], jv["judge_verdict"]))

# 5. Failure examples -------------------------------------------------------
st.header("5. Failure examples")
show = ["question_id", "type", "question", "reference_answer", "rag_answer", "gold_rank", "human_label", "human_note"]
st.subheader("Answers the human marked wrong or not found")
bad = human[human["human_label"] != "correct"]
st.dataframe(bad[show], hide_index=True)
st.caption("gold_rank 0 = the right chunk was not in the top 5 (retrieval miss).")

st.subheader("Where the judges disagreed with the human")
st.dataframe(csv("disagreements.csv"), hide_index=True)

st.subheader("Step 6: fixes tried, one change at a time")
st.dataframe(csv("step6_fixes.csv"), hide_index=True)
nb = csv("labeling_neighbors.csv")
for _, r in nb.iterrows():
    st.write(f"**{r.question_id}: {r.question}**")
    a, b = st.columns(2)
    a.write("Before (BGE-M3 top 5)")
    a.info(r.rag_answer_v1)
    b.write("After (hybrid top 3 + neighbour chunks)")
    b.success(r.rag_answer)
st.caption("Step 6 answers are not human-labeled yet.")
