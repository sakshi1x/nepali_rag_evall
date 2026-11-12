# Directive v1: Nepali RAG Evaluation Harness

> v1 = first draft. Written from intent.md before any code exists. Expect it to be wrong in places; final-directive.md will fix what v1 got wrong.

## Goal (for the coding agent)
Build a small Python project that measures, on the Constitution of Nepal only:
1. How well BM25 and BGE-M3 retrieve the right passage (Recall@5, MRR).
2. Whether 2 LLM judges agree with a human's correct/wrong labels on 30 answers.
3. Whether one fix improves a number.
Then show it in a simple Streamlit demo.

## Rules for the agent
- Do one step at a time. After each step, stop, show the outputs and checks, and wait for the human to say "next".
- Do NOT expand scope: one document, Nepali only, 30 human labels, 2 judges, one fix.
- NEVER fill in the `human_label` column. Leave it empty for the human.
- Never invent numbers. Every metric must come from a script that can be re-run.
- Use `OPENROUTER_API_KEY` from `.env`. Never print it or commit it. Add `.env` to `.gitignore`.
- Cache every LLM call (prompt + model + response) to a `.jsonl` file so reruns don't cost money.
- Use temperature 0 and a fixed random seed (42).
- Before any step that calls an LLM many times, print the number of calls and estimated cost, and wait for "ok".
- Record the model name and prompt version in every results file.

## Inputs
- `assets/नेपालको स_ंविधान unicode भाद्र २०८१_mtbuyjt.pdf` (Unicode PDF, not scanned)
- `baseline-qa.md`: 5 hand-checked Q&A pairs with evidence quotes (used as a sanity check)
- `.env` with `OPENROUTER_API_KEY`

## Outputs (target folder layout)
```
src/            extract.py, chunk.py, gen_qa.py, filter_qa.py, retrieve.py, answer.py, judge.py, metrics.py
data/processed/ pages.jsonl, chunks.jsonl
data/qa/        qa_generated.jsonl, qa_filtered.jsonl, qa_rejected.jsonl
data/labels/    answers_to_label.csv  (human fills human_label)
results/        retrieval_metrics.csv, retrieval_per_question.csv,
                judge_results.csv, judge_agreement.csv, disagreements.csv,
                fix_before_after.csv
cache/          llm_cache.jsonl
app.py          Streamlit demo
README.md       how to run
```

## Steps

### Step 0: Setup
- Create the folders above, `requirements.txt` (pymupdf, rank_bm25, sentence-transformers, chromadb, pandas, streamlit, openai or requests for OpenRouter, python-dotenv).
- Check: `python -c "import fitz, rank_bm25, sentence_transformers, chromadb"` runs without errors.

### Step 1: Extract and chunk
- Extract text page by page with PyMuPDF. Apply Unicode NFC normalization. Save `pages.jsonl` (page, text).
- Chunk by Article (धारा) where the heading can be detected; otherwise ~300 words with ~50-word overlap.
- Each chunk: `chunk_id`, `page`, `article` (if found), `text`.
- Checks:
  - Print page count, chunk count, and min/avg/max chunk length.
  - Print 3 random chunks so the human can read them.
  - All 5 evidence quotes from `baseline-qa.md` must be found in some chunk (exact or after normalizing spaces). Report which ones fail.
  - Count broken-looking text (for example, Q2's evidence in baseline-qa.md has "बमोजजमका" where "बमोजिमका" is expected). Report whether this comes from the PDF itself.

### Step 2: Generate and filter Q&A
- Pick ~60 chunks at random (seed 42). For each, ask an LLM for 2-3 Nepali Q&A pairs in JSON: `question`, `answer`, `evidence` (exact quote from the chunk), `type`.
- Types to mix: fact, number, date, list, negation, why/how. Questions should sound like a real user. Do not start every question with "नेपालको संविधान अनुसार".
- Filter (save rejects with a reason in `qa_rejected.jsonl`):
  - Evidence must be an exact substring of its source chunk.
  - The answer must appear in, or be directly supported by, the evidence.
  - Remove near-duplicate questions.
  - Remove yes/no questions and questions with an empty or overly long answer.
- Target: ~100 kept pairs in `qa_filtered.jsonl`, each with `gold_chunk_id`.
- Checks: print kept/rejected counts by reason and type, and print 10 random kept pairs for the human to spot-check. If more than 3 of the 10 are bad, fix the prompt (not the code) and rerun.

### Step 3: Retrieval (BM25 vs BGE-M3)
- BM25: `rank_bm25`, tokenize on whitespace, strip punctuation (including । and ,).
- BGE-M3: `BAAI/bge-m3` via sentence-transformers. Store vectors in chromadb (persistent, in `data/`).
- For each question, get the top 5 chunks from each method.
- Metrics: Recall@5 (gold chunk in the top 5) and MRR (1/rank of gold chunk, 0 if not in the top 5). Also break them down by question type.
- Outputs: `retrieval_metrics.csv`, `retrieval_per_question.csv`.
- Checks: run the 5 baseline questions first and show the top 1 result for each; metrics must be between 0 and 1. Warn the human that BGE-M3 is ~2 GB and slow on CPU.

### Step 4: Answers and the human labeling sheet
- Use the better retriever from Step 3. Pass the top-5 chunks to an LLM with this instruction: answer in Nepali using only the context, otherwise reply "जानकारी उपलब्ध छैन".
- Pick 30 questions for labeling: a mix of types, including some where retrieval missed the gold chunk.
- Write `answers_to_label.csv`: `id, question, gold_answer, evidence, model_answer, retrieved_ok, human_label (empty), human_note (empty)`.
- Write a short labeling guide at the top of the README: what counts as "correct" (matches the gold fact, nothing false added) and as "wrong".
- STOP. The human labels all 30. The agent does not touch `human_label`.

### Step 5: 2 LLM judges vs human labels
- Two judges from different model families via OpenRouter (models TBD by the human). Same prompt, which returns JSON `{verdict: correct|wrong, reason}`.
- The judge sees the question, gold answer, evidence and model answer.
- Metrics per judge vs human: agreement %, Cohen's kappa, false-positive rate (judge says correct when the human says wrong, divided by the number of human "wrong" labels).
- `disagreements.csv`: every row where a judge disagrees with the human, with the judge's reason. The agent may suggest a failure type; the human confirms or changes it.
- Checks: count invalid JSON responses (must be 0 or retried), and compute kappa by hand on a tiny example to check the function.

### Step 6: One fix, before/after
- Choose ONE fix based on what Steps 3-5 show. The default candidate is to normalize Nepali/English digits and BS date text in both chunks and queries. A judge-prompt fix is another option if the judges are the weak part.
- Change only that one thing and rerun the same metric on the same data.
- Output `fix_before_after.csv`: metric, before, after, change.
- Check: everything else stays identical (same seed, same questions, same models).

### Step 7: Streamlit demo
- `app.py`: a question box; the top-5 passages from BM25 and BGE-M3 side by side with scores; the generated answer; a results tab showing the metrics CSVs.
- Load the saved index; don't rebuild it on every run. No API key in the code.
- Check: `streamlit run app.py` works and the 5 baseline questions return sensible passages.

## Definition of done
- Every CSV in `results/` can be regenerated with a command listed in the README.
- 30 human labels are filled in by the human, not by AI.
- The README states the models used, prompt versions, and known limitations.

## Open questions (to fix in final-directive)
- Which 2 judge models and which answer model? Budget per run?
- Is Article-based chunking reliable on this PDF, or should we use a fixed size?
- Is ~100 Q&A pairs enough, or is it too slow and costly for the deadline?
- Does BGE-M3 run fast enough on this laptop?
