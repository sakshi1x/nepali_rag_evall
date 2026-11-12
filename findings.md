# Findings: Nepali RAG Eval Harness (Steps 1–6)

**As of:** Day 2, Nov 12, 2026, 21:00 NPT · **Source of every number:** `log/log.md` (Entries #5–#22) and `results/`

## Main findings

### 1. OCR was essential for making the Nepali Constitution usable for RAG
The PDF was labelled Unicode, but its text layer was corrupted ("बमोजिम" 0 times vs the broken "बमोजजम" 712 times; 0 of 5 baseline quotes found). Neither ordinary extraction nor filtering out corrupted text produced usable data (0 of 350 chunks clean; the sentence filter kept 0.4% of words). OCR with Tesseract (`nep`, 300 DPI) recovered 39,287 words across 183 pages, with all 5 baseline evidence quotes found after checking them against the page images. However, OCR still missed some Article numbers printed in the margin (261 of 308 headings found), so about 47 Articles were merged into the previous chunk.

### 2. BM25 and BGE-M3 performed almost equally, but BGE-M3 was better on manually written questions
On 177 generated questions, BM25 reached Recall@5 0.955 / MRR 0.862, and BGE-M3 reached Recall@5 0.966 / MRR 0.848. On the 5 manually written questions, BGE-M3 ranked the correct chunk first in 5 of 5 cases, BM25 in 3 of 5. Generated questions may favour keyword retrieval because they reuse words from the source chunks.

### 3. Retrieval failures caused most answer failures, and a retrieval miss can produce a confidently wrong answer
Four answers were "not found", and all four were retrieval misses. q108 showed a more dangerous failure: the correct chunk was missed, yet the model answered confidently from Article 4 (the state) instead of Article 3 (the nation). A RAG system needs to tell "not enough evidence" apart from an answer that only sounds relevant.

### 4. The two AI judges matched each other perfectly, but agreement did not mean they were always correct
Opus 5.5 and Haiku 5.5 gave identical verdicts on all 30 answers, although Haiku cost $0.005 against Opus's $0.16. After the human re-check, both reached 96.7% agreement and Cohen's kappa 0.889 (first pass: 93.3%, kappa 0.762). They caught one human labeling mistake (q108), but both wrongly rejected a supported clause in q111, because they received one evidence sentence instead of the full Article.

### 5. Evaluation quality depends on evidence quality, human verification and realistic test questions
Limitations: generated questions favoured BM25; OCR missed some Article numbers; Nepali used about 60% more tokens than estimated; all three models (answerer and both judges) are from the Claude family. The judges had zero false positives across five wrong cases, but that sample is too small to show they are reliably safe (4 of the 5 were easy "not found" answers). Human verification was needed to find both retrieval and judging errors.

### 6. Step 6: a prompt fix failed, retrieval and context fixes worked
Three fixes were tried, one change at a time (`results/step6_fixes.csv`):
- **Quote-first prompt (failed):** the model must quote the supporting sentence first, and Python checks the quote is really in the chunks. Misses answered "not found" stayed 4/5 and q108 stayed confidently wrong: the model quoted the real Article 4 sentence, so the check passed. The model also wrote things beyond its own quote. Cost $0.36.
- **Hybrid retrieval (worked):** Reciprocal Rank Fusion of the saved BM25 and BGE-M3 top 5 lists, no new model or vectors. On 177 questions Recall@5 went 0.966 → 0.989, MRR 0.848 → 0.883, misses 6 → 2 (q031, q108). The 4 "not found" answers (q016, q019, q020, q169) became real answers. Retrieval $0, re-answer $0.06.
- **Neighbour chunks (worked for q108):** hybrid top 3 plus 3 chunks before and 2 after each. The gold chunk is now in the model's context for 176/177 questions (only q031 missing), at about 2.4× the tokens. q108 now answers with the Article 3 nation traits. Cost $0.02.

Lesson: the q108 failure came from retrieval and chunking (the Article 3 heading was not split, so Article 3 sits inside another chunk), so a prompt could not fix it; more and better context did. Limits: fixes 2 and 3 were re-answered only on the questions they changed (4 and 1), and human labels for all Step 6 answers are still pending.

## Which findings to emphasize

| Priority | Finding | Why it matters |
|---|---|---|
| 1 | OCR was essential | Real-world Nepali document challenge |
| 2 | BM25 vs BGE-M3 | Actual retrieval experiment |
| 3 | q108 retrieval failure | Strongest RAG failure example |
| 4 | AI judges and q111 | Strongest evaluation insight |
| 5 | Human verification and limitations | Shows critical thinking |
| 6 | Step 6 fixes (prompt failed, hybrid + neighbours worked) | Shows fixing the cause, not the symptom |

## Key insight for Step 6: q111

| | |
|---|---|
| What the judges received | One evidence sentence (limited context) |
| What the full Article contained | Article 250(5): "पुन: नियुक्ति हुन सक्ने छैन । तर सदस्यलाई अध्यक्षको पदमा नियुक्ति गर्न सकिनेछ", so the extra clause is supported |
| What this tells us | An AI judge can wrongly reject a correct answer when its evidence is incomplete. The fix may not be a smarter judge, but better evidence for the same judge. |

**Future work (not run, no result claimed):** give the judge the full gold chunk instead of one evidence sentence. Step 6 instead fixed the answer side (see finding 6), because q108 was the more harmful failure.

## Pricing (actual API cost)

Prices used (Anthropic API, per million tokens, input / output): Opus 5.5 $4 / $20 · Sonnet 5.5 $2 / $10 · Haiku 5.5 $0.10 / $0.50. Token counts are from `cache/llm_cache.jsonl`.

| Step | What | Model | Calls | Input tokens | Output tokens | Cost |
|---|---|---|---|---|---|---|
| 2 | Generate Q&A (180 questions) | Opus 5.5 | 60 | 64,044 | 84,921 | $1.95 |
| 3 | BM25 + BGE-M3 retrieval | local (CPU) | – | – | – | $0 (BGE-M3: 50 min on CPU) |
| 4 | Answer 30 questions | Sonnet 5.5 | 30 | 141,399 | 2,655 | $0.31 |
| 5 | Judge 1 | Opus 5.5 | 30 | 14,428 | 5,170 | $0.16 |
| 5 | Judge 2 | Haiku 5.5 | 30 | 14,428 | 6,501 | $0.005 |
| 5 | Re-scoring after label re-check (×2) | cache | 0 | – | – | $0 |
| 6 | Fix 1: quote-first answers (30) | Sonnet 5.5 | 30 | 144,489 | 6,951 | $0.36 |
| 6 | Fix 2: hybrid retrieval | local | – | – | – | $0 |
| 6 | Fix 2: re-answer 4 recovered questions | Sonnet 5.5 | 4 | 25,914 | 405 | $0.056 |
| 6 | Fix 3: re-answer q108 with neighbour chunks | Sonnet 5.5 | 1 | 9,868 | 209 | $0.022 |
| | **Total** | | **185** | **414,570** | **106,812** | **≈ $2.87** |

**Estimates vs actual**
- Step 4: Opus 5.5 was quoted at ~$0.55–1.25 and rejected as too expensive; Sonnet 5.5 was quoted at $0.30–0.60 and cost $0.31.
- Step 5: quoted at $0.25–0.95; it cost $0.17.
- Nepali text needed about 0.75 tokens per character in Step 4, about 60% more than the first estimate.
- Output tokens drive cost: in Step 2, output was 87% of the cost; in Step 4 it was only 9%.
- Haiku 5.5 gave the same 30 verdicts as Opus 5.5 at about 1/34 of the cost.
- Step 6: all three fixes cost $0.44 together; the two that worked cost $0.08.
