# Findings: Nepali RAG Eval Harness (Steps 1–5)

**As of:** Day 2, Nov 12, 2026, 20:12 NPT · **Source of every number:** `log/log.md` (Entries #5–#20) and `results/`

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

## Which findings to emphasize

| Priority | Finding | Why it matters |
|---|---|---|
| 1 | OCR was essential | Real-world Nepali document challenge |
| 2 | BM25 vs BGE-M3 | Actual retrieval experiment |
| 3 | q108 retrieval failure | Strongest RAG failure example |
| 4 | AI judges and q111 | Strongest evaluation insight |
| 5 | Human verification and limitations | Shows critical thinking |

## Key insight for Step 6: q111

| | |
|---|---|
| What the judges received | One evidence sentence (limited context) |
| What the full Article contained | Article 250(5): "पुन: नियुक्ति हुन सक्ने छैन । तर सदस्यलाई अध्यक्षको पदमा नियुक्ति गर्न सकिनेछ", so the extra clause is supported |
| What this tells us | An AI judge can wrongly reject a correct answer when its evidence is incomplete. The fix may not be a smarter judge, but better evidence for the same judge. |

**Planned Step 6 experiment (not run yet, no result claimed):** give the judge the full gold chunk instead of one evidence sentence, keep everything else the same, and compare before/after.

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
| | **Total** | | **150** | **234,299** | **99,247** | **≈ $2.43** |

**Estimates vs actual**
- Step 4: Opus 5.5 was quoted at ~$0.55–1.25 and rejected as too expensive; Sonnet 5.5 was quoted at $0.30–0.60 and cost $0.31.
- Step 5: quoted at $0.25–0.95; it cost $0.17.
- Nepali text needed about 0.75 tokens per character in Step 4, about 60% more than the first estimate.
- Output tokens drive cost: in Step 2, output was 87% of the cost; in Step 4 it was only 9%.
- Haiku 5.5 gave the same 30 verdicts as Opus 5.5 at about 1/34 of the cost.
