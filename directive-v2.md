# Directive v2: Nepali RAG Evaluation Harness

> v2 = written on Nov 12, 2026 after Step 1 failed: the PDF's text layer turned out to be corrupted. v1 is kept unchanged in directive-v1.md. Every change below is tied to a real event (see "Changes from v1" and log/log.md Entries #5-#11).

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
- Never fix, replace or guess corrupted characters. If most of the text is broken, do not fall back to "skip the broken parts"; stop and report.
- LLM steps (2, 4, 5) run on the human's own PC (OpenRouter is not reachable from Claude's environment).
- Delete temporary files (page images, temp folders) right after they are used.
- Never edit an old directive. A new version is written only after a real failure, shown as a diff, and saved after approval.

## Inputs
- `assets/नेपालको स_ंविधान unicode भाद्र २०८१_mtbuyjt.pdf`. The pages look correct, but the copy-paste text layer is corrupted, so the text is read by OCR.
- `assets/ocr/nep.traineddata` (Tesseract Nepali model, tessdata_best)
- `baseline-qa.md`: 5 hand-checked Q&A pairs with evidence quotes (used as a sanity check)
- `.env` with `OPENROUTER_API_KEY`

## Outputs (target folder layout)
```
src/            ocr.py, extract.py, chunk.py, filter_lines.py, check_step1.py, gen_qa.py, filter_qa.py, retrieve.py, answer.py, judge.py, metrics.py
data/processed/ pages.jsonl, chunks.jsonl   (v1 text-layer output, kept for comparison only)
                chunks_clean.jsonl, chunks_rejected.jsonl, validation_report.txt (failed skip test, kept)
data/ocr/       pages_ocr*.jsonl, chunks_ocr.jsonl, ocr_quality_report.txt
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
- Create the folders above, `requirements.txt` (pypdf, rank_bm25, sentence-transformers, chromadb, pandas, streamlit, openai or requests for OpenRouter, python-dotenv).
- Check: `python -c "import pypdf, rank_bm25, sentence_transformers, chromadb"` runs without errors. For OCR: `tesseract --version` and `pdftoppm -v` work, and `assets/ocr/nep.traineddata` exists.

### Step 1: OCR, quality gate, chunk
**1a. OCR (replaces text-layer extraction):**
- Render each page at 300 dpi grayscale (`pdftoppm`), run Tesseract with `-l nep`, NFC-normalize. Script: `src/ocr.py`.
- Delete each page image right after OCR; remove the temp folder at the end. The script resumes if stopped.
- Output: `data/ocr/pages_ocr*.jsonl` (`page`, `text`). The v1 text-layer files stay unchanged for comparison.

**1b. Quality gate (must pass before chunking):**
- Count known broken forms (बमोजजम, िुनेछ, गनव, कायव, प्रमिमनमध); they must be 0 or close to 0.
- Count vowel signs in impossible positions (at the start of a word, two in a row); report the rate per 100 words.
- All 5 evidence quotes from `baseline-qa.md` must be found (exact, or after normalizing spaces). Report any that are missing.
- Print 3 random pages; the human compares them with the PDF on screen.
- Write `data/ocr/ocr_quality_report.txt`. If the gate fails, STOP and report. Do not skip or patch the text.

**1c. Clean and chunk:**
- Remove page-header lines, including OCR garbage versions of `www.lawcommission.gov.np` (lines with almost no Devanagari).
- Chunk by Article (धारा) where the heading is detected (`^[०-९]+\.` + title + `ः`); otherwise ~300 words with ~50-word overlap. Output `data/ocr/chunks_ocr.jsonl` with `chunk_id`, `page`, `article`, `text`.
- Checks: page count, chunk count, min/avg/max chunk length; Article numbers 1-308 found (report any missing); 3 random chunks for the human to read.

### Step 2: Generate and filter Q&A
- Input: `data/ocr/chunks_ocr.jsonl` (not the v1 chunks). Pick ~60 chunks at random (seed 42). For each, ask an LLM for 2-3 Nepali Q&A pairs in JSON: `question`, `answer`, `evidence` (exact quote from the chunk), `type`.
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

## Changes from v1
| v1 rule | v2 rule | Reason (real event) |
|---|---|---|
| Extract text with PyMuPDF from the PDF text layer | OCR the page images (300 dpi, Tesseract `nep`); the text layer is used only for comparison | Text layer is corrupted: "बमोजिम" 0 times vs "बमोजजम" 712, "हुनेछ" 0 vs "िुनेछ" 474; 0 of 5 baseline quotes found (Entry #5) |
| Text quality checked after chunking | Quality gate (1b) before chunking; stop if it fails | Corruption was only discovered after chunking (Entry #5) |
| No rule on corrupted text | Never guess or fix characters; don't fall back to "skip broken parts" when most text is broken | Skip test: 0 of 350 chunks clean; sentence filter kept 5 chunks = 0.4% of words, and those were still broken (Entries #7, #9) |
| Header removed by exact text match | Also remove OCR header garbage lines | Header was read as "फाए/फा-]8फ/ट0ा11551010" on page 156 (Entry #11) |
| LLM steps can run anywhere | LLM steps run on the human's PC | OpenRouter blocked in Claude's environment (Entry #6) |
| PyMuPDF in requirements | pypdf (text layer, comparison only) | PyMuPDF could not be installed in Claude's environment (Entry #5) |
| No cleanup rule | Delete temp images and folders right after OCR | Human's request (Entry #10) |

## Known failures & limitations
- The "Unicode" PDF from lawcommission.gov.np has a corrupted text layer (font mapping). Two tools (pypdf, pdftotext) gave the same errors, so the problem is in the PDF.
- Skipping corrupted text did not work: 0 of 350 chunks were clean, and the sentence-level filter kept 0.4% of words, which still contained errors the detector missed ("पाररि", "विमधः", "लामग").
- Re-downloading gave an identical copy of the same PDF (same MD5). Other government PDFs (Law Commission 2021 upload, Madhesh OCA) could not be fetched from Claude's environment.
- OCR is not perfect. Errors seen in the 3-page test: "अनुकलता" (अनुकूलता), "पेसट्ठी" (पैंसट्ठी), garbage header line; "रङ्ग" vs "रङ" spelling variant.
- OCR speed: about 30 seconds per page (about 90 minutes for 183 pages, single worker).

## Open questions (to fix in final-directive)
- Does the full OCR pass the quality gate on all pages (tables, schedules, maps in the schedules)?
- Which 2 judge models and which answer model? Budget per run?
- Is Article-based chunking reliable on this PDF, or should we use a fixed size?
- Is ~100 Q&A pairs enough, or is it too slow and costly for the deadline?
- Does BGE-M3 run fast enough on this laptop?
