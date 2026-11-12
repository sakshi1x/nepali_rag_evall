# Final Directive: Nepali RAG Evaluation Harness

> final = written on Nov 12, 2026, 21:00 NPT, after Steps 1–6 were built and run. It describes the build as it was actually done, so someone could rebuild it from this file. directive-v1, v2 and v3 are kept unchanged. The section "Plan (v3) vs what we actually did" lists every difference, each tied to a real event in log/log.md. Step 7 (Streamlit) is not built yet; its rules are the plan.

## Goal (for the coding agent)
Build a small Python project that measures, on the Constitution of Nepal only:
1. How well BM25 and BGE-M3 retrieve the right passage (Recall@5, MRR).
2. Whether 2 LLM judges agree with a human's correct/wrong labels on 30 answers.
3. Whether a fix improves a number. Try one change at a time and report every fix you tried, including the ones that failed.
Then show it in a simple Streamlit demo.

## Rules for the agent
- Do one step at a time. After each step, stop, show the outputs and checks, and wait for the human to say "next".
- Do NOT expand scope: one document, Nepali only, 30 human labels, 2 judges.
- NEVER fill in the `human_label` column. If the human asks to change a label, do it only on their explicit word, write who changed it and why in `human_note`, and keep a backup of the old file.
- Never invent numbers. Every metric must come from a script that can be re-run.
- Use `ANTHROPIC_API_KEY` from `.env`. Never print it or commit it. Add `.env` to `.gitignore`.
- Cache every LLM call (model + messages + settings + response + token counts) in `cache/llm_cache.jsonl`, so reruns and re-scoring cost $0.
- Do not send `temperature` (current Claude models reject it). Repeatability comes from the cache. Use the fixed seed 42 for every random choice.
- Before any paid step, print the number of calls and an estimated cost, and wait for "ok". For Nepali, estimate about 0.75 tokens per character (the first estimate was 60% too low).
- Pick the cheapest model that is good enough for each step, and say why.
- Record the model name and prompt version in every results file.
- Never fix, replace or guess corrupted characters. If most of the text is broken, stop and report; do not fall back to "skip the broken parts".
- Paid LLM steps (2, 4, 5, 6) and BGE-M3 run on the human's PC, in the venv `C:\venvs\nre` (Python 3.12, outside OneDrive). Claude's environments cannot reach the API or Hugging Face.
- Never write a new result over an old one. A fix writes to a new file, and any edited file gets a backup in `log/` first.
- Delete temporary files (page images, temp folders) right after they are used.
- After every step, append the log lines to `log/log.md` (Entry #N, Nepal time), including rejected outputs.
- Never edit an old directive. A new version is written only after a real failure, shown as a diff, and saved after approval.

## Inputs
- `assets/नेपालको स_ंविधान unicode भाद्र २०८१_mtbuyjt.pdf`. The pages look correct, but the copy-paste text layer is corrupted, so the text is read by OCR.
- `assets/ocr/nep.traineddata` (Tesseract Nepali model, tessdata_best).
- `baseline-qa.md`: 5 hand-written Q&A pairs, with evidence quotes checked against the page images.
- `.env` with `ANTHROPIC_API_KEY`.

## Outputs (actual folder layout)
```
src/            ocr.py, ocr_quality.py, chunk_ocr.py      (Step 1, used)
                extract.py, chunk.py, filter_lines.py, check_step1.py   (v1 text-layer attempt, kept for comparison)
                llm.py (Claude client + cache), gen_qa.py, filter_qa.py, retrieve.py, answer.py, judge.py, hybrid.py
data/processed/ v1 text-layer output and the failed skip test (kept, not used)
data/ocr/       pages_ocr*.jsonl, chunks_ocr.jsonl, ocr_quality_report.txt
data/qa/        qa_generated.jsonl, qa_filtered.jsonl, qa_rejected.jsonl
data/chroma/    saved BGE-M3 vectors (reused; changing chunk text means a 50-minute re-encode)
results/        retrieval_per_question.csv, retrieval_metrics.csv, baseline_top1.txt
                labeling.csv (answers, empty labels), labeling_human.csv (human labels)
                judge_verdicts.csv, judge_metrics.csv, disagreements.csv
                labeling_v2.csv, fix_before_after.csv             (fix 1)
                retrieval_metrics_hybrid.csv, fix2_before_after.csv, labeling_hybrid.csv   (fix 2)
                labeling_neighbors.csv                            (fix 3)
                step6_fixes.csv                                   (all fixes, one row each)
cache/          llm_cache.jsonl
log/            log.md, backups of every edited file
findings.md     findings + actual cost
app.py          Streamlit demo (Step 7, not built yet)
README.md       how to run (not written yet)
```

## Steps

### Step 0: Setup
- Python 3.12 venv at `C:\venvs\nre` (a venv inside OneDrive with Python 3.14 was blocked by Windows App Control on a DLL).
- `requirements.txt`: pypdf, anthropic, python-dotenv, rank_bm25, sentence-transformers, chromadb, pandas, streamlit.
- Check: the imports work; `tesseract --version` and `pdftoppm -v` work; `assets/ocr/nep.traineddata` exists.

### Step 1: OCR, quality gate, chunk
Unchanged from directive-v3 (Steps 1a–1c): OCR at 300 dpi with Tesseract `nep`; a quality gate before chunking (broken forms, vowel positions, 5/5 baseline quotes found while ignoring U+200C/U+200D, quotes checked against page images); chunk by Article at numbered and unnumbered headings, never guess a missing number, ~300 words with ~50-word overlap.
- Result: 183 pages, 39,287 words, 0 broken forms, 5/5 quotes; 311 chunks; 261 of 308 headings found.
- Known gap: an unnumbered heading is split only when "(१)" follows it. 13 one-clause Articles (for example Article 3 "राष्ट्र", "राष्ट्रभाषा", "शपथ") were not split. This caused the q108 failure. A rebuild should also split a short heading line followed by one clause.

### Step 2: Generate and filter Q&A
- Input `data/ocr/chunks_ocr.jsonl`. 60 random chunks (seed 42), 3 Nepali Q&A pairs each, as JSON: `question`, `answer`, `evidence` (exact quote), `type`. Model: Opus 5.5.
- Filter: evidence must be an exact substring of its chunk; the answer must be supported by the evidence; no near-duplicates; no yes/no questions; no empty or very long answers. Save rejects with a reason.
- Result: 180 generated, 177 kept, 3 rejected (1 unsupported, 2 near-duplicates). Cost $1.95.
- Check: print 10 random kept pairs for the human, and read the full evidence, not a short preview. Merge type names the model invents (it wrote "why/how", "how" and "why").

### Step 3: Retrieval (BM25 vs BGE-M3)
- BM25: `rank_bm25` on whitespace tokens after NFC, removing ZWNJ/ZWJ and punctuation (including ।).
- BGE-M3: `BAAI/bge-m3` via sentence-transformers, cosine, vectors saved in `data/chroma` and reused.
- Gold rule: a hit is the gold chunk OR any chunk that contains the full evidence sentence (chunks overlap, and some sentences repeat across Articles).
- Metrics: Recall@5 and MRR, overall and by type; the 5 baseline questions reported separately.
- Result: BM25 0.955 / 0.862; BGE-M3 0.966 / 0.848; baseline at rank 1: BGE-M3 5/5, BM25 3/5. BGE-M3 took 50 minutes on CPU.

### Step 4: Answers and the human labeling sheet
- Retriever: BGE-M3 top 5, read from the saved Step 3 results (no re-encode).
- Prompt `ans-v1`: answer in Nepali using only the context, otherwise reply "not found". Model: Sonnet 5.5 (Opus was quoted at $0.55–1.25, too high for this step).
- 30 questions (seed 42): the 5 baseline questions, 5 BGE-M3 misses, then filled to 5 per type group (number, negation, list, why/how, fact). Date questions are left out.
- Output `results/labeling.csv` (UTF-8 with BOM for Excel): `question_id, type, question, reference_answer, evidence, rag_answer, retrieved_chunk_ids, gold_rank, human_label (empty), human_note (empty)`.
- Labeling rule: "correct" = matches the reference fact with nothing false added; "wrong" otherwise; "not found" counts as wrong.
- STOP. The human labels all 30 into `results/labeling_human.csv`. Result: 25 correct, 1 wrong, 4 not found. Cost $0.31.

### Step 5: 2 LLM judges vs human labels
- Judges: Opus 5.5 and Haiku 5.5 (both Claude, because only the Anthropic API is used). Same prompt `judge-v1`, JSON `{verdict, reason}`. The judge sees the question, reference answer, evidence sentence and RAG answer.
- "not found" is mapped to "wrong" in the script; the labels file is not changed.
- Metrics per judge: agreement %, Cohen's kappa, false-positive rate, false negatives. Check kappa on a hand-worked example first. Invalid JSON must be 0 or retried.
- `disagreements.csv`: every disagreement with the judge's reason; the human fills `failure_type`.
- When a judge disagrees with the human, the human re-checks the row against the chunk before the final numbers.
- Result: both judges gave identical verdicts: 96.7% agreement, kappa 0.889, 0/5 false positives, 1 false negative (q111: the judge saw one sentence, the supporting clause is in Article 250(5)). Cost $0.17.

### Step 6: Fixes, one change at a time
- Choose each fix from what Steps 3–5 showed. Change one thing, keep everything else identical (questions, seed, model, prompt), and write before/after to a new file.
- What was run:
  1. Quote-first prompt (`ans-v2`, quote must be found in the chunks): no improvement; q108 still wrong. $0.36.
  2. Hybrid retrieval (RRF, K=60, of the saved BM25 + BGE-M3 top 5): Recall@5 0.966 → 0.989, MRR 0.848 → 0.883, misses 6 → 2; the 4 "not found" questions got real answers. $0.06.
  3. Neighbour chunks (hybrid top 3 + 3 chunks before / 2 after): gold chunk in context for 176/177 at ~2.4× tokens; q108 now correct. $0.02.
- Rule for the rebuild: measure retrieval changes on all 177 questions ($0), and re-answer only the questions whose context changed. Say clearly that those were not a full re-run of 30.
- Recommended pipeline after Step 6: hybrid retrieval + neighbour chunks.
- Pending: human labels for `labeling_v2.csv` (30), `labeling_hybrid.csv` (4), `labeling_neighbors.csv` (1).

### Step 7: Streamlit demo (not built yet)
- `app.py`: a question box; the top 5 from BM25, BGE-M3 and hybrid side by side with scores; the generated answer; a results tab with the metrics CSVs and `step6_fixes.csv`.
- Load the saved index and vectors; never rebuild on start. No API key in the code. Answers use the cache where possible.
- Check: `streamlit run app.py` works and the 5 baseline questions return sensible passages.

## Definition of done
- Every CSV in `results/` can be regenerated with a command listed in the README.
- 30 human labels are filled in by the human, not by AI.
- The README states the models used, prompt versions, costs and known limitations.

## Plan (v3) vs what we actually did
| directive-v3 said | What we actually did | Why (real event) |
|---|---|---|
| LLMs via OpenRouter (`OPENROUTER_API_KEY`) | Anthropic API directly (`ANTHROPIC_API_KEY`) | Human's choice; OpenRouter was blocked from Claude's environment (Entries #6, #15) |
| Temperature 0 | No temperature sent; repeatability from the cache | Current Claude models reject `temperature` (Entry #15) |
| Two judges from different model families | Opus 5.5 + Haiku 5.5, both Claude | Only the Anthropic API was used (Entries #15, #20). Limitation: same family |
| Answer model not set | Sonnet 5.5 for answers | Opus quoted $0.55–1.25, rejected as too expensive; Sonnet cost $0.31 (Entry #18) |
| Venv not specified | Python 3.12 venv at `C:\venvs\nre` | Python 3.14 venv in OneDrive hit a DLL block (Windows App Control) |
| ~100 kept Q&A pairs | 180 generated, 177 kept | 60 chunks × 3 pairs, and the filter rejected only 3 (Entry #16) |
| Type list: fact, number, date, list, negation, why/how | Model also wrote "how" and "why"; kept as written | Model drift (Entry #16) |
| Gold = gold chunk | Gold chunk OR any chunk containing the full evidence sentence | Chunks overlap by 50 words and some sentences repeat across Articles (Entry #17) |
| Answer fallback "जानकारी उपलब्ध छैन" | "not found" | Human's wording in the Step 4 request (Entry #18) |
| `data/labels/answers_to_label.csv` with `id, gold_answer, model_answer, retrieved_ok` | `results/labeling.csv` with `question_id, reference_answer, rag_answer, retrieved_chunk_ids, gold_rank` | Human gave the column list in the Step 4 request (Entry #18) |
| Labels correct / wrong | Human used a third label "not found"; mapped to wrong for Step 5 | 0 "wrong" labels made the false-positive rate undefined (Entries #19, #20) |
| Labeling guide in the README | Rule agreed in chat; README not written yet | README is part of Step 7 / write-up |
| `judge_results.csv`, `judge_agreement.csv` | `judge_verdicts.csv`, `judge_metrics.csv` | Naming only |
| `src/metrics.py` | Metrics inside `retrieve.py` and `judge.py`; added `llm.py`, `ocr_quality.py`, `chunk_ocr.py`, `hybrid.py` | Simpler; each step's script computes its own metric |
| Labels final once filled | Human relabeled q108 correct → wrong after the judges flagged it; q111 kept correct | Human re-check against the chunks (Entry #20) |
| ONE fix; default = normalize digits / BS dates | Three fixes, each one change: quote-first prompt (failed), hybrid retrieval, neighbour chunks. Normalization was not tried | The failures found (q108, q111, 4 "not found" misses) pointed at retrieval and context, not digits. Fix 1 failed, so the human chose more fixes and to report all (Entry #22) |
| Fix re-runs the same metric on the same data | Retrieval metrics on all 177; answers re-run only for the questions each fix changed (30, 4, 1) | Cost and time; re-answering all 30 for fix 2 would need a full re-label (Entry #22) |
| Streamlit demo | Not built yet | Pending (Step 7) |

Earlier changes (v1 → v2 → v3: OCR instead of the text layer, quality gate, no guessing characters, header garbage removal, ZWNJ-ignoring quote match, page-image checks, unnumbered headings) are listed in directive-v3.md and still apply.

## Known failures & limitations
- The PDF's text layer is corrupted; all text comes from OCR. OCR drops margin Article numbers (261/308 headings) and makes small spelling errors ("सार्वभीम" for "सार्वभौम").
- 13 one-clause Articles were not split into their own chunk; this caused q108.
- Generated questions reuse the chunk's words, which probably makes BM25 and all retrieval numbers look better than with real users.
- Answerer and both judges are Claude models. The judges' 0/5 false positives is a small sample (4 of 5 were easy "not found" cases).
- The judges saw one evidence sentence, not the full Article, which caused the q111 false negative. Giving the judge the full gold chunk is untested future work.
- Fixes 2 and 3 were re-answered only on the questions they changed; Step 6 answers are not human-labeled yet.
- BGE-M3 encoding takes about 50 minutes on CPU; any chunk change forces a re-encode.
- Total API cost: 185 calls, 414,570 input / 106,812 output tokens, ≈ $2.87.
