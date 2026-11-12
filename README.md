# Nepali RAG Evaluation Harness (Constitution of Nepal)

A small, honest test bench for question answering over a Nepali legal document. It measures how well a system finds the right passage, whether AI judges grade answers the way a human does, and whether a fix actually helps.

Every number in this README comes from the files in `results/` and the step-by-step log in `log/log.md`. Nothing was typed in by hand.

---

## 1. The problem

Retrieval-augmented generation (RAG) means you search a document for passages and let an LLM answer **only** from those passages. For Nepali this is harder than for English:

- **Bad source text.** The official "Unicode" PDF of the Constitution has a corrupted copy-paste text layer ("बमोजिम" appears 0 times, the broken "बमोजजम" 712 times). Any system that trusts the PDF text is searching garbage.
- **Unknown retrieval quality.** Does keyword search (BM25) or a multilingual embedding model (BGE-M3) find the right Article more often?
- **Unknown judge quality.** Teams often let an LLM grade answers. Does that grade match a careful human?

This project answers those three questions on one document, with 177 generated questions, 5 hand-written questions, 30 human-labeled answers and 2 LLM judges. It also tests three fixes, one change at a time.

---

## 2. What is in this folder

```
assets/            the PDF + assets/ocr/nep.traineddata (Tesseract Nepali model)
baseline-qa.md     5 hand-written questions with exact evidence quotes (sanity check)
src/               all scripts (one per step, listed below) + src/app.py (Streamlit page)
data/ocr/          OCR pages, quality report, chunks_ocr.jsonl (311 chunks)
data/qa/           generated, kept and rejected questions
data/chroma/       saved BGE-M3 vectors (so you never re-encode by accident)
results/           every metric and label file (CSV)
cache/             llm_cache.jsonl: every LLM call, so reruns cost $0 (not in git)
log/log.md         what was done, when, with which tool, and what was kept or rejected
directive-v1/v2/v3.md, final-directive.md   the instructions given to the coding agent, and how they changed
findings.md        the findings, with the full cost table
STREAMLIT.md       how to run the demo page
```

---

## 3. Setup (once)

### 3.1 Python
Use **Python 3.12** in a virtual environment **outside** OneDrive/Dropbox. On Windows, a Python 3.14 venv inside OneDrive was blocked by App Control (a DLL would not load).

```powershell
py -3.12 -m venv C:\venvs\nre
C:\venvs\nre\Scripts\python.exe -m pip install -r requirements.txt
```
`requirements.txt`: pypdf, anthropic, python-dotenv, rank_bm25, sentence-transformers, chromadb, pandas, streamlit.

In the commands below, `python` means `C:\venvs\nre\Scripts\python.exe` (or activate the venv first). Run every command **from the project folder**.

### 3.2 OCR tools (only needed for Step 1)
- **Tesseract** and **Poppler** (`pdftoppm`, `pdfinfo`) on your PATH. On Linux: `sudo apt install tesseract-ocr poppler-utils`.
- The Nepali model: download `nep.traineddata` from the `tesseract-ocr/tessdata_best` repository on GitHub and put it in `assets/ocr/`.
- Check: `tesseract --version` and `pdftoppm -v` both print a version.

### 3.3 API key (only for the paid steps 2, 4, 5, 6)
Copy `.env.example` to `.env` and fill it in. **Never commit `.env`** (it is in `.gitignore`).
```
ANTHROPIC_API_KEY=sk-ant-...
QA_MODEL=claude-opus-5-5          # model that writes the questions
ANSWER_MODEL=claude-sonnet-5-5    # optional; model that answers (otherwise QA_MODEL)
```
Every call is cached in `cache/llm_cache.jsonl`. Re-running a step with the same inputs costs $0. Every paid script has a `--dry-run` that prints the number of calls and the prompt size without calling anything. **Always run the dry run first.**

---

## 4. How to run it, step by step

| Step | Command | Output | Cost | Time |
|---|---|---|---|---|
| 1a OCR | `python src/ocr.py --pages 1-3` (test), then `python src/ocr.py` | `data/ocr/pages_ocr.jsonl` | $0 | ~30 s/page |
| 1b Quality gate | `python src/ocr_quality.py` | `data/ocr/ocr_quality_report.txt` | $0 | seconds |
| 1c Chunk | `python src/chunk_ocr.py` | `data/ocr/chunks_ocr.jsonl` | $0 | seconds |
| 2a Questions | `python src/gen_qa.py --dry-run`, then `python src/gen_qa.py` | `data/qa/qa_generated.jsonl` | ~$1.95 (Opus) | minutes |
| 2b Filter | `python src/filter_qa.py` | `data/qa/qa_filtered.jsonl`, `qa_rejected.jsonl` | $0 | seconds |
| 3 Retrieval | `python src/retrieve.py --method both` | `results/retrieval_*.csv`, `baseline_top1.txt` | $0 | BGE-M3: ~50 min on CPU the first time |
| 4 Answers | `python src/answer.py --dry-run`, then `python src/answer.py --model claude-sonnet-5-5` | `results/labeling.csv` | ~$0.31 | ~1 min |
| 4b **Human labels** | fill `human_label` by hand, save as `results/labeling_human.csv` | | your time | ~30–45 min |
| 5 Judges | `python src/judge.py --selftest`, `--dry-run`, then `python src/judge.py` | `results/judge_*.csv`, `disagreements.csv` | ~$0.17 | ~1 min |
| 6 Fixes | see 4.6 | `results/*fix*.csv`, `labeling_v2/hybrid/neighbors.csv` | ~$0.44 | minutes |
| 7 Demo | `streamlit run src/app.py` | browser page at http://localhost:8501 | $0 | seconds |

### 4.1 Step 1: OCR, quality gate, chunk
1. Test 3 pages first: `python src/ocr.py --pages 1-3`. Open the PDF and compare by eye.
2. Run all pages: `python src/ocr.py`. It resumes if stopped, and deletes each page image right after reading it. To go faster, run two copies on different page ranges, e.g. `--pages 1-92 --part a` and `--pages 93-183 --part b` (outputs `pages_ocr_a.jsonl`, `pages_ocr_b.jsonl`; all are read together).
3. Run the gate: `python src/ocr_quality.py`. It must say PASS: 0 known broken forms, few vowel signs in impossible positions, and **all 5 baseline quotes found**. If a quote is missing, look at the **page image** before changing anything. Copy-pasted or AI-retyped quotes silently change spellings.
4. Chunk: `python src/chunk_ocr.py`. It prints the number of chunks and how many Article headings it found (here 311 chunks, 261 of 308 headings). A missing Article number is never guessed; the chunk gets `number_missing_in_ocr: true`.

### 4.2 Step 2: questions
`gen_qa.py` picks 60 random chunks (seed 42) and asks the model for 2–3 Nepali Q&A pairs each, with an exact evidence quote. `filter_qa.py` drops pairs whose evidence is not an exact substring of the chunk, whose answer is not supported, near-duplicates and yes/no questions, and writes each reject with its reason. **Read 10 kept pairs yourself, using the full evidence and not a short preview.**

### 4.3 Step 3: retrieval
`retrieve.py` runs BM25 and BGE-M3 and writes Recall@5 and MRR, overall and by question type, plus the top-1 chunk for the 5 baseline questions.
- A question counts as **found** if a top-5 chunk is its gold chunk **or** any chunk that contains its full evidence sentence (chunks overlap by 50 words).
- BGE-M3 downloads ~2 GB the first time. Vectors are saved in `data/chroma/` and reused. **If chunk text changes, everything is re-encoded (~50 min on CPU).**
- `--method bm25` alone is fast and needs no download.
- After re-running Step 3, re-run `python src/hybrid.py` so the hybrid rows match.

### 4.4 Step 4: answers and the human labeling sheet
`answer.py` picks 30 questions (seed 42): the 5 baseline questions, 5 where BGE-M3 missed, and the rest filled to 5 per type group. It answers each from the saved BGE-M3 top 5 only, or replies "not found".

Then **a human labels every row**. Open `results/labeling.csv` in Excel and fill `human_label` with `correct`, `wrong` or `not found`, plus a short `human_note` if useful. Save it as `results/labeling_human.csv`.
- **correct** = gives the reference fact and adds nothing false.
- **wrong** = misses the fact or adds something false.
- **not found** = the system said it could not find it (counted as wrong in Step 5).

The AI never fills `human_label`.

### 4.5 Step 5: two LLM judges
`judge.py --selftest` checks the Cohen's kappa function on a hand-worked example (must print 0.5). Then the two judges (Opus 5.5 and Haiku 5.5, same prompt `judge-v1`) grade all 30 answers. The script writes agreement %, kappa, false positives and false negatives per judge, and `disagreements.csv`. In `disagreements.csv`, the human fills `failure_type` and re-checks each disagreement against the chunk.

### 4.6 Step 6: fixes (one change at a time)
```
python src/answer.py --quote-first --model claude-sonnet-5-5                       # fix 1: quote-first prompt -> results/labeling_v2.csv
python src/hybrid.py                                                               # fix 2: hybrid BM25 + BGE-M3 retrieval, $0
python src/answer.py --hybrid-only q016,q019,q020,q169 --model claude-sonnet-5-5   # fix 2: re-answer the questions it recovered
python src/answer.py --hybrid-only q108 --neighbors 3,3,2 --model claude-sonnet-5-5 # fix 3: top 3 + 3 chunks before / 2 after
```
The question ids are the ones from this run. On your own data, use the ids that `results/fix2_before_after.csv` and `retrieval_per_question.csv` show as changed. Each fix writes to a **new** file. Older results are never overwritten.

### 4.7 Step 7: the demo page
```powershell
C:\venvs\nre\Scripts\streamlit.exe run src\app.py
```
The page shows: document → questions → Recall@5/MRR → judge agreement chart → failure examples. It only reads saved files: no API calls, no downloads. Details are in `STREAMLIT.md`.

---

## 5. Using your own PDF

The pipeline is built for the Constitution of Nepal, but every step works on another Nepali (Devanagari) document if you change the places below. Do them in this order.

1. **Put your PDF in `assets/`.** In `src/ocr.py` change `PDF = sorted((ROOT / "assets").glob("*mtbuyjt.pdf"))[0]` to match your file name.
2. **Check whether you need OCR at all.** Copy a paragraph from the PDF into a text editor. If it reads correctly, you could extract the text directly. If you see broken words (letters swapped, vowel signs in odd places), use OCR as here. For a non-Nepali document, download that language's `.traineddata` and change `-l nep` in `ocr.py`.
3. **Write your own `baseline-qa.md`**: 5 questions in the same format (`### Q1`, `**Type:**`, `**Question:**`, `**Answer:**`, `**Evidence from text:** "exact quote"`). Copy each quote from the **page image**, letter by letter, not from copy-paste.
4. **Adjust the quality gate** in `src/ocr_quality.py`:
   - `range(1, 184)`: set it to your page count + 1.
   - `BROKEN`: list the broken word forms you saw in your PDF's text layer (or leave it, if you only use OCR).
5. **Adjust the chunker** in `src/chunk_ocr.py`. It splits at Article headings like `१६. title:` and at unnumbered `title: (१)`. If your document uses other headings (Sections, Chapters, numbered paragraphs), change the `ARTICLE` and `UNNUMBERED` patterns, and the `range(1, 309)` used for the heading count. If there are no clear headings, fixed ~300-word chunks with 50-word overlap are a safe start.
6. **Change the document name in the prompts.** `src/gen_qa.py`, `src/answer.py` and `src/judge.py` say "Constitution of Nepal" (`नेपालको संविधान`). Replace it with your document's name.
7. **Delete the old outputs** before running on new data, otherwise old rows mix with new ones: `data/ocr/`, `data/qa/`, `data/chroma/`, `results/`. Keep `cache/`; it is keyed by the exact prompt, so new text never hits old answers.
8. Run Steps 1–7 as in section 4. Do the dry runs first and check the cost.

---

## 6. Results

### 6.1 Document and questions
| | Value |
|---|---|
| Pages OCR'd | 183 (39,287 words, 0 known broken forms, 5/5 baseline quotes) |
| Chunks | 311 (Article headings found: 261 of 308) |
| Questions generated / kept / rejected | 180 / 177 / 3 |

### 6.2 Retrieval (177 generated questions)
| Method | Recall@5 | MRR | Baseline 5 at rank 1 |
|---|---|---|---|
| BM25 | 0.955 | 0.862 | 3 / 5 |
| BGE-M3 | 0.966 | 0.848 | 5 / 5 |
| Hybrid RRF (Step 6 fix 2) | **0.989** | **0.883** | 5 / 5 |

### 6.3 Answers (30, Sonnet 5.5, BGE-M3 top 5), human labels
| correct | wrong | not found |
|---|---|---|
| 25 | 1 (q108) | 4 (q016, q019, q020, q169: all retrieval misses) |

### 6.4 Judges vs human (30 answers, "not found" = wrong)
| Judge | Agreement | Cohen's kappa | False positives | False negatives | Cost |
|---|---|---|---|---|---|
| Opus 5.5 | 96.7% | 0.889 | 0 / 5 | 1 (q111) | $0.16 |
| Haiku 5.5 | 96.7% | 0.889 | 0 / 5 | 1 (q111) | $0.005 |

The two judges gave identical verdicts on all 30 answers.

### 6.5 Step 6 fixes
| Fix | What changed | Before | After | Cost | Result |
|---|---|---|---|---|---|
| 1 Quote-first prompt | prompt only | not found on misses 4/5; q108 wrong | same | $0.36 | no improvement |
| 2 Hybrid retrieval | retrieval only | R@5 0.966, MRR 0.848, misses 6 | R@5 0.989, MRR 0.883, misses 2 | $0 + $0.06 | 4 "not found" became real answers |
| 3 Neighbour chunks | context only | gold in context 175/177 | 176/177 (~2.4× tokens) | $0.02 | q108 now gives the Article 3 traits |

**Pending:** human labels for the Step 6 answers (`labeling_v2.csv` 30 rows, `labeling_hybrid.csv` 4, `labeling_neighbors.csv` 1). Until then, "became real answers" and "q108 now correct" are Claude's reading, not human-confirmed.

### 6.6 Cost
185 API calls, 414,570 input / 106,812 output tokens, **≈ $2.87 in total**. Most of it ($1.95) went on question generation, mainly output tokens. Full table in `findings.md`.

---

## 7. Failures and limitations

1. **Corrupted PDF text layer.** Extraction with two tools gave the same broken text. Skipping broken parts did not work (0 of 350 chunks clean; a line filter kept 0.4% of words). OCR fixed it.
2. **OCR drops Article numbers in the margin.** 261 of 308 headings were found. About 47 Articles share a chunk with the Article before them, and 13 one-clause Articles were never split. OCR also makes small spelling errors ("सार्वभीम" for "सार्वभौम").
3. **q108: a confident wrong answer.** The question asks for the traits of the *nation* (Article 3). Retrieval missed that chunk, and the model answered from Article 4 (the *state*) without saying it was unsure. A quote-first prompt did **not** fix it, because the model quoted a real but wrong-subject sentence. More context (neighbour chunks) did.
4. **q111: the judges were wrong, not the answer.** The answer included a clause from Article 250(5). Both judges marked it wrong because they saw only one evidence sentence, not the whole Article. Giving the judge the full chunk is untested future work.
5. **Generated questions are too easy for keyword search.** They reuse the chunk's own words, so all Recall numbers are probably higher than with real users. On the 5 hand-written questions BM25 found the right chunk first only 3 times.
6. **Same model family.** The question writer, the answerer and both judges are Claude models. 0 false positives out of 5 is a very small sample, and 4 of the 5 were easy "not found" cases.
7. **Fixes 2 and 3** were re-answered only on the questions they changed (4 and 1), not on a full re-run of all 30.
8. **Human mistakes happen too.** The first human labels had q108 as correct; the judges flagged it and a re-check changed it to wrong. Both versions are kept (`log/labeling_human.before-relabel.csv`).
9. **Slow on CPU.** BGE-M3 encoding took ~50 minutes; OCR took ~35 minutes with 2 workers.

---

## 8. How this was built

The build was done with an AI coding agent under written directives. `directive-v1.md` → `v2` (switch to OCR) → `v3` (quote and heading fixes) → `final-directive.md` (what was actually done, with a plan-vs-actual table). Every change was tied to a real failure. Every action, including rejected outputs, is in `log/log.md`. Human labels were made by a human only.
