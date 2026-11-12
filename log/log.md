## Entry #2: Baseline (Manual vs AI-Assisted Q&A)
**Date:** Nov 11, 2026

**What I did:**
Generated 5 baseline question-answer pairs grounded in the Nepali Constitution 
(नेपालको संविधान) using Gemini Notebook assistance. Saved in `baseline-qa.md`.

**Time taken:** 
5 pairs = [FILL_MINUTES] minutes (about [CALCULATE_PER_PAIR] minutes per pair).
At this speed, 100 pairs would take about [CALCULATE_HOURS] hours.

**What was written:**
- Q1 (location): Capital of Nepal → काठमाडौं
- Q2 (number): Members of the House of Representatives → २७५ जना
- Q3 (fact): Script of official government language → देवनागरी लिपि
- Q4 (number/date): Commencement date of the constitution → संवत् २०७२ साल असोज ३ गते
- Q5 (fact): National animal of Nepal → गाई

**What I noticed:**
- Verified all evidence quotes against the source text (`नेपालको संविधान unicode भाद्र २०८१.pdf`) to confirm 100% precision.
- All 5 questions are simple factual lookups; none test multi-hop reasoning, negation, lists, or "why/how" logic.
- Q4 is categorized as "number" but functions as a specific calendar date.
- Question phrasing begins repeatedly with standard formal prefixes ("नेपालको संविधान अनुसार..."), which differs from natural user search queries.

**Kept / rejected:**
- **Kept:** Standardized format schema (`Type`, `Question`, `Answer`, `Evidence from text`).
- **Rejected:** Chatbot conversational closing lines (`💡 would you like more Q&A sets?`) were trimmed from the production file.
- **Next steps:** Introduce varied query intent types, multi-constraint questions, and natural phrasing variations.

**Why this matters:**
Serves as the baseline dataset for speed, precision, and quality comparisons against subsequent RAG test sets.

## Entry #3: intent.md draft (with Claude)
**Date:** Nov 11, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 01:30 | Claude | add Entry #2 to the AI log | Claude saved it to ai-log.md (I later moved my log to log/log.md) | kept
- 01:35 | Claude | start intent.md | Claude asked me 5 interview questions (problem, who, why hard, success, out of scope) | kept
- 02:10 | Claude | draft intent.md from my 5 answers | draft created; Claude trimmed it to project scope: one document only, added hand labels / 2 judges / kappa / one fix, made numeral+date normalization the "one fix", moved OCR/Preeti out of scope (PDF is already Unicode), changed "three days" to "by Nov 15" | pending my review

**Open items:**
- Review intent.md and accept or reject Claude's scope changes.
- Fill in the [FILL_MINUTES] time placeholders in Entry #2.

## Entry #4: directive-v1.md (with Claude)
**Date:** Nov 11, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 03:05 | Claude | write directive-v1.md from intent.md (inputs, outputs, steps, checks) | Claude wrote a 7-step spec (setup, extract+chunk, Q&A gen+filter, BM25 vs BGE-M3, answers + labeling sheet, 2 judges, one fix, Streamlit) with rules for the agent (stop after each step, never fill human_label, cache LLM calls, ask before spending) | pending my review

**Noticed while writing:**
- baseline-qa.md Q2 evidence has "बमोजजमका" (expected "बमोजिमका"). It may be a PDF text-extraction problem. Added a check for it in Step 1.

**Open items:**
- Choose the answer model and the 2 judge models (OpenRouter).
- Review directive-v1.md; keep it unpolished (v1 is meant to be improved into final-directive.md).

## Entry #5: Step 1, extract and chunk (with Claude)
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 00:50 | Claude | follow Step 1 of directive-v1: extract and chunk the PDF | wrote src/extract.py, src/chunk.py, src/check_step1.py; made data/processed/pages.jsonl (183 pages) and chunks.jsonl (350 chunks, one per Article, long ones split at 300 words) | chunking kept; text quality REJECTED (see below)
- 00:50 | Claude | (deviation) PyMuPDF could not be installed in Claude's environment (no network), so pypdf was used; pdftotext gave the same text | kept for now

**What the checks showed (real numbers from check_step1.py):**
- Article headings found: 305 of 308 (missing 96, 135, 143).
- Words per chunk: min 9 / avg 120 / max 300.
- 0 of 5 baseline-qa.md evidence quotes were found in the extracted text.
- The PDF's text layer is broken even though it is a "Unicode" PDF: "बमोजिम" appears 0 times but "बमोजजम" 712 times; "हुनेछ" 0 vs "िुनेछ" 474; "गर्न" 0 vs "गनव" 349; "प्रतिनिधि" 0 vs "प्रमिमनमध" 150. The same errors come out of both pypdf and pdftotext, so the problem is in the PDF's font mapping, not the extraction tool.
- baseline-qa.md Q2's evidence ("बमोजजमका") contains this same glitch, so part of that quote came from the broken text layer.
- intent.md says "My PDF is already Unicode text, OCR out of scope". This is now shown to be wrong.

**Open items:**
- Decide: find a clean text copy of the Constitution, or OCR the PDF, or continue with broken text.

## Entry #6: Step 2, generate and filter Q&A (prepared, NOT run yet)
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 00:55 | Claude | generate and filter questions per directive (Step 2) | Claude did not generate yet: chunks still have the broken text from Step 1, so questions and evidence would carry the same errors | on hold
- 00:55 | Claude | (same) | wrote src/llm.py (OpenRouter + cache), src/gen_qa.py (60 chunks, 2-3 pairs each, prompt gen-v1, --dry-run), src/filter_qa.py (evidence must be in chunk, answer supported, no yes/no, no near-duplicates, rejects keep a reason); added requirements.txt, .env.example, .gitignore | pending review
- 00:55 | Claude | (same) | dry run: 60 calls, about 45k-90k input tokens + about 24k output tokens | kept
- 00:55 | Claude | (same) | OpenRouter is NOT reachable from Claude's environments (network blocked), so the generation must run on my own PC | noted

**Blocked on:**
- Text source decision (clean copy / OCR / keep broken).
- Choosing QA_MODEL and adding OPENROUTER_API_KEY to .env.

## Entry #7: Plan to skip corrupted chunks, tested before changing anything
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 01:10 | Claude | change Step 1 to detect + skip corrupted chunks (chunks_clean.jsonl / chunks_rejected.jsonl), update directive, show changes first, wait for approval | before editing, Claude measured how many chunks would survive (read-only test, no files changed) | plan on hold

**What the test showed (real numbers):**
- Detector signals: a vowel sign at the start of a word, two vowel signs in a row, and known broken words (बमोजजम, गनव, कायव, िुन ...).
- Chunks with zero signals: 0 of 350.
- Allowing up to 5 signals per chunk: 22 chunks kept = 1.3% of words.
- Median: about 31 corruption signals per 100 words.
- Sentence level: 52 of 1,394 sentences have no signal (1.5% of words), but they still contain errors the detector misses (e.g. "मममि", "पमन", "अमभयोग").
- 0 of 5 baseline evidence quotes exist anywhere in the extracted text.

**Conclusion so far:** skipping corrupted chunks would leave almost no usable text, and the detector cannot catch every error. Waiting for my decision.

## Entry #8: Decision, no questions from this PDF; search for a clean source
**Date:** Nov 12, 2026

**My decision:** The current PDF is too corrupted. No question generation from it. Keep all existing extraction files and scripts as they are (for comparison). No changes to the directive, code or dataset until I approve a new source.

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 01:18 | Claude (web search + web fetch) | find a clean, official Unicode version of the Constitution, government sites first | found candidates but could NOT download or check any of them (Claude's environment blocks gov.np downloads) | pending
  - lawcommission.gov.np Constitution page: loaded, but it only links an English PDF (2nd amendment)
  - lawcommission.gov.np older Nepali PDF (2021 upload): could not be fetched
  - oca.madhesh.gov.np "दोश्रो संशोधन सहित" PDF (Madhesh Province govt): could not be fetched
  - Nepali Wikisource page: not found
  - Hugging Face datasets: exist, but not official, and the viewer did not load
- 01:18 | Claude | plan | I download 1-2 government Nepali PDFs into assets/candidates/; Claude runs a read-only quality check on them; if none pass, fall back to OCR (Tesseract + Nepali) | pending my approval
- 01:22 | Claude | check the downloaded PDF | new file assets/...mtbuyjt2.pdf is byte-for-byte identical to the original (same MD5 6fe01226...), so it is the same corrupted PDF, not a new source; no check run | rejected

## Entry #9: Skip broken lines, then generate questions
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 01:24 | Claude | skip the broken lines exactly, then generate questions | wrote src/filter_lines.py: splits each chunk into sentences (at ।), drops any sentence with a corruption sign, never fixes or guesses characters; originals untouched; writes chunks_clean.jsonl, chunks_rejected.jsonl (page + reason) and validation_report.txt | script kept
- 01:24 | Claude | (same) | result: 183 pages, 350 chunks, only 5 chunks kept, 0.4% of words retained, 1,429 sentences rejected; 0 of 5 baseline quotes found | data REJECTED
- 01:24 | Claude | (same) | the 5 "clean" chunks are still broken in ways the detector misses ("पाररि", "विमधः", "लामग", "मनधावरण", "सम्िनु पछव") | question generation NOT run
- 01:24 | Claude | (same) | OCR check: Tesseract 4.1.1 is installed in Claude's environment but has no Nepali language file, and downloads are blocked there | next: I download nep.traineddata so Claude can run OCR

## Entry #10: Decision, use OCR; directive versioning rules
**Date:** Nov 12, 2026

**My decision:** Use OCR on the PDF page images (the pages look correct, only the copy-paste text layer is broken). Clean up temp files and resources immediately after OCR.

**Directive rules from now on:** never edit an old directive; each new version (v2, v3...) is written after a real failure, includes a "Changes from v1" table (v1 rule → v2 rule → reason) and a "Known failures & limitations" section, is shown to me as a diff, and is saved only after I approve. The PDF corruption is the trigger for directive-v2.

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 01:31 | Claude | use OCR, clean up afterwards | wrote src/ocr.py: renders each page at 300 dpi, runs Tesseract (Nepali), deletes each page image right after, removes the temp folder at the end, writes data/ocr/pages_ocr.jsonl (originals untouched), resumes if stopped | kept
- 01:31 | Claude | (same) | waiting for nep.traineddata in assets/ocr/ before the 3-page test | pending

## Entry #11: OCR 3-page test
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 01:37 | Claude | test OCR on 3 pages | moved nep.traineddata from assets/ to assets/ocr/; OCR'd pages 4, 42, 156 (Articles 9, 84, 288); about 26-33 seconds per page; temp images deleted, no temp folder left | kept
- 01:37 | Claude | (same) | quality on these 3 pages (623 words): बमोजिम 22 / बमोजजम 0, हुनेछ 13 / िुनेछ 0, प्रतिनिधि 8 / प्रमिमनमध 0; 0 vowel signs in impossible positions; 3 of 3 baseline quotes on these pages found word for word (capital, 275 members, national animal) | kept
- 01:37 | Claude | (same) | OCR errors seen: "अनुकलता" (should be अनुकूलता), "पेसट्ठी" (should be पैंसट्ठी), page header read as garbage ("फाए/फा-]8फ/ट0ा11551010"), "रङ्ग" instead of "रङ" (both valid spellings) | noted as known limitation
- 01:37 | Claude | (same) | estimate for all 183 pages: about 90 minutes one at a time, maybe about 50 minutes with 2 in parallel | pending
- 01:37 | Claude | propose directive-v2 (diff only, not saved) | shown in chat, waiting for my approval | pending

## Entry #12: directive-v2 saved; full OCR started
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 01:42 | Claude | APPROVE directive-v2 | saved directive-v2.md: the full spec, with Step 1 rewritten as OCR → quality gate → chunk, new agent rules (never guess characters, LLM steps on my PC, delete temp files, never edit old directives), plus "Changes from v1" (7 rows) and "Known failures & limitations" sections. directive-v1.md unchanged (same MD5 98a5db89...) | kept
- 01:42 | Claude | run full OCR | src/ocr.py got a --part option so 2 workers can run in parallel without writing to the same file; runs in batches of ~2 minutes; temp images deleted after each page | running

## Entry #13: Full OCR done; quality gate result
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 02:18 | Claude | run full OCR | all 183 pages OCR'd (data/ocr/pages_ocr.jsonl, _a, _b), 2 workers, about 35 minutes; every page image deleted right after use; temp folders, batch script and logs removed; no OCR process left running; data/ocr = 688 KB | kept
- 02:18 | Claude | quality gate (src/ocr_quality.py) | 39,287 words; known broken forms all 0; vowel signs in impossible positions 3 (0.01 per 100 words); baseline quotes 2 of 5 found exactly → GATE: FAIL (on quotes only) | stopped before chunking, as directive-v2 says
- 02:18 | Claude | why 3 quotes "failed" | all 3 sentences ARE in the OCR text, with small differences: Q2: my baseline quote itself has the corrupted "बमोजजमका" (OCR has the correct "बमोजिमका"); Q4: OCR has "महीनाको", baseline has "महिनाको", plus an invisible zero-width character after "संवत्"; Q5: OCR has "रङ्ग", baseline has "रङ" | pending my decision
- 02:18 | Claude | (same) | src/chunk_ocr.py written but NOT run (waiting for gate decision) | pending
- 02:27 | Claude | I pasted text copied from PDF pages 168 and 4 to settle the spellings | the paste is the corrupted copy-paste text layer again (e.g. "संिि्", "िनुेछ"), so it can't settle spellings by itself. Q4: the paste shows "मिीनाको" (long ी), which supports the OCR "महीनाको" (my baseline "महिनाको" was wrong). Q5: the paste shows "रि", which could be रङ or रङ्ग, so it is still unclear and must be checked by eye on screen | Q4 resolved, Q5 open
- 02:30 | Claude | I pasted a clean-looking version of pages 168 and 4 | Claude rendered both pages as images and looked at them directly (images deleted afterwards). The page shows "महीनाको" (long ी) and "रङ्ग सिम्रिक" / "रङ्गको", so the OCR was right on both. My pasted version differs from the page in several places ("महिनाको", "रङ", "बहुसङ्ख्यक" vs page "बहुसंख्यक", "अङ्कित" vs "अंकित", "तरिका" vs "तरीका"), so it was not a word-for-word copy | pasted version rejected as a reference; OCR kept

## Entry #14: Gate passed; OCR text chunked
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 02:35 | Claude | OK, fix baseline quotes + ignore invisible characters, then do it | backup saved as log/baseline-qa.before-ocr-fix.md; baseline-qa.md evidence fixed to match the page images: Q4 "महीनाको", Q5 "रङ्ग" (Q2 "बमोजिमका" was already fixed by me) | kept
- 02:35 | Claude | (same) | src/ocr_quality.py now ignores zero-width characters (U+200C/U+200D) when matching quotes; rerun: 5 of 5 baseline quotes found, broken forms 0, 3 bad vowel positions in 39,287 words → GATE: PASS | kept
- 02:35 | Claude | (same) | first chunk run found only 198 Article numbers: OCR often drops the Article number in the left margin (e.g. "बालबालिकाको हक: (१)" with no "३९."). Fixed chunk_ocr.py to also split at unnumbered headings (short title + ः + "(१)"); the number is NOT guessed (article = null, number_missing_in_ocr = true) | kept
- 02:35 | Claude | (same) | result: data/ocr/chunks_ocr.jsonl = 311 chunks, 12/134/300 words (min/avg/max); 261 of 308 Article headings detected (201 with number, 60 without); the other ~47 Articles are merged into the previous chunk (text is kept, only the split is missed); 6 header-noise lines dropped | kept, limitation noted
- 02:35 | Claude | (same) | stopped before Step 2 (question generation) for my review | pending
- 02:37 | Claude | update the directive too | per my versioning rule (never edit an old version), Claude proposed directive-v3 as a diff in chat instead of editing v2: 4 changes tied to Entries #13-#14 | pending my approval
- 02:38 | Claude | APPROVE directive-v3 | saved directive-v3.md: full spec, gate ignores zero-width characters, baseline quotes checked against page images, chunking also splits at unnumbered headings (numbers never guessed), heading check reported not required; new "Changes from v2" table (4 rows) and updated known failures; directive-v1.md and v2 unchanged (MD5 checked) | kept

## Entry #15: Switch LLM provider from OpenRouter to Anthropic
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 02:45 | Claude | use Anthropic instead of OpenRouter (I set ANTHROPIC_API_KEY and QA_MODEL=claude-opus-5-5 in .env) | rewrote src/llm.py with the official anthropic Python SDK: effort "medium", max_tokens 16000, server-side refusal fallback enabled for Opus 5.5, refusals and cut-off answers raise an error, every call cached with model + token usage; requirements.txt: requests → anthropic | kept
- 02:45 | Claude | (same) | gen_qa.py and filter_qa.py now read data/ocr/chunks_ocr.jsonl (as directive-v3 says), not the corrupted v1 chunks | kept
- 02:45 | Claude | (same) | dry run: 60 calls, about 50k-100k input tokens; estimated cost with Opus 5.5 ($4 / $20 per million tokens) about $1-4 including thinking tokens | pending my "go"
- 02:45 | Claude | (same) | 2 deviations from the directive: (1) "temperature 0" is not possible, current Claude models reject the temperature setting, so repeatability comes from the cache; (2) "2 judges from different model families" cannot hold with one provider, so the judges will be 2 different Claude models | noted for final-directive
- 02:45 | Claude | (same) | Claude's environment cannot reach api.anthropic.com, so generation must run on my PC | noted
- 02:54 | pip / PowerShell | install requirements in my venv (Python 3.14, inside the OneDrive folder) | pydantic (needed by the anthropic SDK) installed, but importing it failed: "DLL load failed while importing _pydantic_core: An Application Control policy has blocked this file" (Windows Smart App Control / app control blocked the compiled pydantic_core file) | blocked
- 02:54 | Claude | (same) | suggested fix: new venv OUTSIDE OneDrive with Python 3.12 (e.g. C:\venvs\nre), and if still blocked check Windows Security → App & browser control → Smart App Control; added venv/ to .gitignore | pending
- 02:58 | Claude (session on my PC, PowerShell) | fix the pydantic DLL block | only Python 3.14 was installed; installed Python 3.12.10 for my user with winget (no admin); created a new venv at C:\venvs\nre (outside OneDrive); pip install anthropic python-dotenv; import test printed "ok 2.8.0", so the DLL is no longer blocked; no Windows security settings changed; old .\venv, project files and .env untouched; dry run only (60 calls, no API cost) | kept

## Entry #16: Step 2, generate and filter Q&A
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 03:38 | gen_qa.py on my PC (C:\venvs\nre, claude-opus-5-5) | generate Q&A from 60 OCR chunks | 180 questions in data/qa/qa_generated.jsonl; 60 API calls, all served by claude-opus-5-5; 64,044 input + 84,921 output tokens ≈ $1.95 (from cache/llm_cache.jsonl) | kept
- 12:01 | Claude (filter_qa.py, no API) | filter the generated Q&A | kept 177, rejected 3 (1 answer not supported by evidence, 2 near-duplicates); kept by type: fact 62, number 40, list 34, negation 23, why/how 6, how 6, date 4, why 2 | kept
- 12:01 | Claude | (same) | spot-check: q035 looked wrong in the short preview ("दश वर्ष"), but the full evidence says धारा ११(६) naturalized citizens need "कम्तीमा पाँच वर्ष", so the answer is right. Lesson: check the full evidence, not the 120-character preview. I still need to check the 10 printed samples by eye | pending my review
- 12:01 | Claude | (same) | the model used 3 type names not in the prompt list ("why/how", "how", "why"); kept as written, to merge later if needed | noted

## Entry #17: Step 3, retrieval BM25 vs BGE-M3
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 12:01 | Claude | build BM25 + embedding search, report Recall@5 and MRR | wrote src/retrieve.py (--method bm25 / bge / both): BM25 = rank_bm25 on whitespace tokens, punctuation (। , etc.) and zero-width characters removed; BGE-M3 = BAAI/bge-m3 via sentence-transformers, vectors saved in data/chroma (cosine) and reused; outputs results/retrieval_per_question.csv, retrieval_metrics.csv, baseline_top1.txt | kept
- 12:01 | Claude | (same) | gold rule: a hit = the gold chunk OR any chunk that contains the full evidence sentence (chunks overlap by 50 words). 150 questions have 1 gold chunk, 23 have 2; 9 have 5-14 because the evidence is boilerplate repeated in many Articles ("निजको उमेर पेसट्ठी वर्ष पूरा भएमा") | kept, noted as limitation
- 12:01 | Claude (BM25 run in Claude's cloud environment, same data) | BM25 | Recall@5 0.955, MRR 0.862 on 177 questions (strict gold-chunk-only: 0.949 / 0.835, almost the same). Weakest type: number (0.925 / 0.782) | kept
- 12:01 | Claude | (same) | baseline 5 questions, BM25: Q1 capital rank 1, Q2 house size rank 4 (top1 = impeachment Article), Q3 language rank 1, Q4 start date rank 4 (top1 = Article 4), Q5 national animal rank 1 | kept
- 12:01 | Claude | (same) | warning: BM25 scores are probably too good, because the questions were generated from the chunks and reuse their words. Real users would word things differently | noted for write-up
- 12:01 | Claude | (same) | BGE-M3 cannot run in Claude's environments (huggingface.co blocked); needs my PC: pip install sentence-transformers chromadb rank_bm25 into C:\venvs\nre, ~2 GB model download, slow on CPU | pending
- 12:05-13:15 | Claude (on my PC, PowerShell, C:\venvs\nre) | install retrieval libraries and run BM25 + BGE-M3 | installed rank_bm25 0.2.2, sentence-transformers 6.3.0, chromadb 1.5.9, torch 2.15.0+cpu (install ~11 min); `python src\retrieve.py --method both` took 50 min on CPU (incl. ~2 GB BGE-M3 download + encoding 311 chunks); vectors saved in data\chroma; no DLL or memory errors; no settings changed | kept
- 13:15 | Claude | (same) | results on 177 generated questions: BM25 Recall@5 0.955 / MRR 0.862; BGE-M3 Recall@5 0.966 / MRR 0.848, almost a tie. BGE-M3 weaker on list (0.912) and why/how (0.833); BM25 weaker on number (0.925 / 0.782) | kept
- 13:15 | Claude | (same) | baseline 5 hand-written questions: BGE-M3 ranked the gold chunk 1st for 5/5; BM25 3/5 (House size and start date at rank 4). Hand-written questions are closer to real users, so this favours BGE-M3. The date/why/how groups have only 2-6 questions, too few to conclude anything | kept
- 13:15 | Claude | (same) | recommended BGE-M3 as the retriever for Step 4 | pending my choice
- 13:15 | Claude | (same) | deadline risk: re-encoding BGE-M3 costs ~50 min on CPU; any Step 6 fix that changes chunk text forces a re-encode | noted

## Entry #18: Step 4, RAG answers + human labeling sheet
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 15:20 | Claude | use BGE-M3; pick 30 questions (mix of types, the 5 baseline, ~5 BGE-M3 misses); answer using ONLY the top-5 chunks, "not found" otherwise; save results/labeling.csv; don't fill human_label; tell me the cost first | wrote src/answer.py (prompt ans-v1). It reads the saved BGE-M3 top-5 from results/retrieval_per_question.csv, so chunk text and vectors are untouched and nothing is re-encoded. Selection fixed with seed 42: 5 baseline + 5 misses (q016, q019, q020, q108, q169) + filled to 5 per group (number, negation, list, why/how, fact); the 4 date questions left out (not in my list) | kept
- 15:20 | Claude | (same) | "not found" used as I asked; directive-v3 had the Nepali phrase "जानकारी उपलब्ध छैन" | noted for final-directive
- 15:25 | Claude | (same) | dry run: 30 calls, 187,683 prompt characters; Opus 5.5 estimate ~$0.55-1.25 | rejected by me: too expensive for this step
- 15:32 | me | use Sonnet or a cheaper model | Claude re-quoted: Sonnet 5.5 ~$0.30-0.60, Haiku 5.5 ~$0.01-0.03; recommended Sonnet (better Nepali, keeps Opus free to be a judge in Step 5); added --model option to answer.py | I chose Sonnet
- 15:35 | Claude (on my PC, C:\venvs\nre) | python src\answer.py --model claude-sonnet-5-5 | 30 answers, no errors, all served by claude-sonnet-5-5; 141,399 input + 2,655 output tokens = $0.31. Input tokens were ~60% more than the 88k estimate (Nepali text uses more tokens than the character ratio assumed) | kept
- 15:35 | Claude | (same) | 4 answers are "not found" (q016, q019, q020, q169), all BGE-M3 retrieval misses, so the model did not invent those. The 5th miss, q108, still got a full answer although the gold chunk was not in the top 5: I must check if the retrieved chunks really support it | pending my label
- 15:35 | Claude | (same) | results/labeling.csv: 30 rows, columns question_id, type, question, reference_answer, evidence, rag_answer, retrieved_chunk_ids, gold_rank, human_label, human_note; human_label and human_note empty in all 30 rows; saved as UTF-8 with BOM so Excel shows Nepali | kept
- 15:35 | Claude | (same) | NEXT: I label all 30 rows myself (correct / wrong + note). AI does not touch human_label | pending me

## Entry #19: Human labels (30 answers)
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 16:13 | me (by hand, no AI) | label all 30 RAG answers | saved as results/"labeling_HUMAN - labeling.csv.csv": 26 correct, 4 "not found" (q016, q019, q020, q169), 0 wrong; no notes | kept
- 16:19 | Claude (check only, labels not changed) | check my labeled file | 30 rows, same 10 columns; question, reference_answer, rag_answer, retrieved_chunk_ids and gold_rank identical to results/labeling.csv (0 changed cells); copied to results/labeling_human.csv (clean name for scripts), original kept | kept
- 16:19 | Claude | (same) | problem for Step 5: with 0 "wrong" labels the false-positive rate is 0/0 (undefined) and Cohen's kappa has almost nothing to measure; "not found" is a 3rd label the directive did not define | pending my decision

## Entry #20: Step 5, two LLM judges vs my labels
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 16:23 | me | mark "not found" as wrong | Claude did NOT edit my labels: results/labeling_human.csv stays as I wrote it; src/judge.py maps "not found" -> "wrong" when scoring, so humans = 26 correct / 4 wrong | kept
- 16:30 | Claude | prepare Step 5 | wrote src/judge.py (prompt judge-v1): same prompt for both judges, judge sees question + reference answer + evidence + system answer, returns JSON {verdict, reason}; one retry on invalid JSON, counted; metrics per judge: agreement %, Cohen's kappa, false-positive rate (judge "correct" when I said wrong / 4), false negatives; outputs results/judge_verdicts.csv, judge_metrics.csv, disagreements.csv (failure_type left empty for me) | kept
- 16:30 | Claude | (same) | judges: claude-opus-5-5 and claude-haiku-5-5. Not Sonnet, because Sonnet wrote the answers (a model may go easy on its own answers). Both are Claude models, so "different model families" from the directive still does not hold (deviation already noted in Entry #15) | pending my go
- 16:30 | Claude | (same) | kappa self-test passed: hand example (3 of 4 agree, chance 0.5) = 0.5; perfect agreement = 1.0 | kept
- 16:30 | Claude | (same) | dry run: 60 calls, 25,674 prompt chars per judge (~19k tokens using Step 4's real ratio); estimate Opus ~$0.20-0.90, Haiku < $0.03 | pending my go
- 16:35 | Claude (on my PC, C:\venvs\nre) | python src\judge.py (after my "go") | 60 calls, no errors, 0 invalid JSON, 0 retries; served_by claude-opus-5-5 x30 and claude-haiku-5-5 x30 (no fallback); cost Opus $0.16 + Haiku $0.005 = ~$0.17, below the $0.25-0.95 estimate | kept
- 16:35 | Claude | (same) | results: both judges agree with me on 28/30 = 93.3%, Cohen's kappa 0.762, false-positive rate 0/4 = 0.0, false negatives 2 (judge "wrong" where I said "correct"). Both judges gave exactly the same 30 verdicts | kept
- 16:35 | Claude | (same) | disagreements (results/disagreements.csv, 4 rows = 2 questions x 2 judges): q108 - answer describes the Nepali state (Article 4), reference lists the nation's traits (Article 3); q111 - core answer right (no reappointment) but adds a clause after "तर" that judges say is not supported by the evidence | pending my re-check of q108/q111 (labels stay mine; don't change them just because judges disagree)
- 16:35 | Claude | (same) | limits: only 4 "wrong" cases and all 4 are easy "not found" answers, so the 0% false-positive rate says little; the two judges are both Claude models and agreed 100% with each other; failure_type column empty for me to fill | noted for write-up
- 16:40 | me | asked Claude: are my labels for q108 and q111 true or false? | Claude checked the OCR chunk text (did not change any label): q108 - answer is Article 4 text ("नेपाल ... राज्य हो"), the question asks about the nation (राष्ट्र), defined in Article 3 (gold chunk o0001: "राष्ट्र: बहुजातीय, बहुभाषिक, बहुधार्मिक, बहुसांस्कृतिक विशेषतायुक्त..."); none of the 4 reference traits is in the answer. q111 - the extra clause is real: Article 250(5), chunk o0240, says "तर सदस्यलाई अध्यक्षको पदमा नियुक्ति गर्न सकिनेछ", so the answer is supported and the judges were wrong | pending my final label
- 16:40 | Claude | (same) | finding: the judges only see the one-sentence evidence, not the full Article, so they marked a true extra detail (q111) as "unsupported". Candidate for the Step 6 fix: give the judge the full gold chunk | noted
- 16:37 | me | make q108 and q111 "wrong" instead of "correct" in my human labels | Claude edited only those 2 rows of results/labeling_human.csv (human_note says "changed ... by me after re-check"); backup of before: log/labeling_human.before-relabel.csv; my original export file left unchanged. Labels now: 24 correct, 2 wrong, 4 not found (= 6 wrong for scoring) | kept
- 16:38 | Claude | re-score judges with my new labels | rerun of src/judge.py used only cached verdicts (cache still 150 rows, no API calls, $0): both judges 30/30 = 100% agreement, kappa 1.000, false positives 0/6, false negatives 0; disagreements.csv now empty. Old metrics kept in log/judge_metrics.before-relabel.csv and log/disagreements.before-relabel.csv | kept
- 16:38 | Claude | (same) | warning for the write-up: q111's extra clause IS in Article 250(5), so the judges' "wrong" was based on missing context; by relabeling q111 the judges now look perfect. The before/after relabel numbers (93.3%/0.762 -> 100%/1.000) must both be reported, with the reason | noted
- 16:43 | me | correction: q108 was my labeling mistake, make it wrong; q111 stays correct | Claude set q111 back to "correct" in results/labeling_human.csv (q108 stays "wrong"); human_note explains both. Labels now: 25 correct, 1 wrong (q108), 4 not found = 5 wrong for scoring | kept
- 16:44 | Claude | re-score judges from cache (no API calls, cache still 150 rows, $0) | both judges: 29/30 = 96.7% agreement, Cohen's kappa 0.889, false positives 0/5, false negatives 1 (q111). disagreements.csv = q111 x 2 judges | kept
- 16:44 | Claude | (same) | summary for the write-up: first pass 93.3% / kappa 0.762 (judges disagreed on q108 and q111); after my re-check the judges caught 1 real human labeling mistake (q108) and made 1 real mistake themselves (q111: they called a true clause from Article 250(5) "unsupported" because they only saw the one-sentence evidence) | kept
- 16:44 | Claude | (same) | note: the 16:38 "100% / kappa 1.000" result is replaced by this one (q111 relabel undone) | noted
- 20:10 | me | is Step 5 (test the AI judges) finished? | Claude: judge part done (2 judges, agreement %, kappa, false positives, disagreements table in results/disagreements.csv); left for me: (1) fill failure_type for the 2 disagreements (Claude's suggestion only: q108 = human labeling error caught by judges + retrieval miss; q111 = judges too strict from missing context, negation question; none about numbers or wrong language), (2) write 3-5 finding bullets myself | pending me
- 20:12 | me | log everything so far; list in chat everything that can be written as findings | Claude added these lines and listed all measured facts from Steps 1-5 in chat as raw material (facts only, the wording of the findings is mine) | kept

**Status at end of Day 2 (20:12):** Steps 1-5 done. Open: failure_type for q108/q111, my 3-5 finding bullets, Step 6 (one fix: candidate = give the judge the full gold chunk instead of one evidence sentence, no BGE-M3 re-encode needed), Step 7 Streamlit, final-directive.md, README/write-up, videos. Deadline ~Nov 15.

## Entry #21: findings.md (Steps 1-5) with pricing
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 20:19 | me + Claude | write my 5 main findings into a document, plus the pricing | Claude saved findings.md in the project folder: my 5 findings (OCR essential; BM25 vs BGE-M3; q108 confident wrong answer after a retrieval miss; judges identical but q111 shows missing-context error; limitations + human verification), the priority table, the q111 insight with the planned Step 6 experiment marked "not run yet", and a cost table from cache/llm_cache.jsonl: 150 API calls, 234,299 input + 99,247 output tokens, about $2.43 in total (Step 2 $1.95, Step 4 $0.31, Step 5 $0.17, re-scoring $0) | kept
- 20:27 | me | worst failure (I called it q111, it is q108: Article 3 nation vs Article 4 state): suggest ONE practical fix, no bigger LLM | Claude: cause = Article 3 text is buried in chunk o0001 with Articles 1-2 (OCR read heading "राष्ट्र" as "राष्ट्ः" and dropped the number, so no split), BGE-M3 ranked it below 5th, and the answer prompt let a nearby fact through. Proposed fix: "quote first, then answer" prompt (copy the one sentence that directly answers, else "not found") + Python check that the quote is really in the retrieved chunks. Test: rerun the same 30 questions on the same saved top-5 (~$0.31 Sonnet), only the prompt changed; pass = q108 and all 5 retrieval misses become "not found" and none of the 25 correct answers are lost. Not run, no result claimed. Step 6 allows one fix: this (q108) or the judge full-chunk fix (q111); Claude recommends this one | pending my choice

## Entry #22: Step 6, one fix: quote-first answer prompt
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 20:35 | me | apply the quote-first answer prompt (my one Step 6 fix, chosen over the judge full-chunk fix) | Claude added prompt ans-v2 to src/answer.py behind a new flag --quote-first; prompt v1 and its output are untouched (backup of the old script: log/answer.before-quote-first.py). ans-v2: copy the ONE sentence that directly answers this question (a related but different subject does not count), then answer from it only; else empty quote + "not found"; returns JSON {quote, answer} | kept
- 20:38 | Claude | (same) | added a code check: the quote must be in the retrieved top-5 chunks (exact, or >= 0.9 of its characters in order, so a model fixing an OCR typo like सार्वभीम -> सार्वभौम still passes); otherwise the answer is forced to "not found". Tested: q108's Article 4 sentence scores 0.993 (in the chunks), an invented sentence 0.508 (rejected), empty quote 0. Note: the check only catches invented quotes; whether the quote is about the right subject depends on the prompt | kept
- 20:38 | Claude | (same) | kept identical to Step 4: same 30 questions (seed 42), same saved BGE-M3 top-5, same model (claude-sonnet-5-5); only the prompt changes. Output goes to a NEW file results/labeling_v2.csv with quote, quote_in_chunks, rag_answer, rag_answer_v1 and my v1 label for reference; human_label empty for me | kept
- 20:38 | Claude | (same) | dry run: 30 calls, 197,133 prompt chars; estimate ~$0.35-0.50 with Sonnet (a bit above the $0.31 of v1 because of the longer prompt and the quote in the output) | kept
- 20:40 | Claude (on my PC, C:\venvs\nre) | python src\answer.py --quote-first --model claude-sonnet-5-5 | 30 answers, no errors, 0 invalid JSON, all served by claude-sonnet-5-5; 144,489 input + 6,951 output tokens = $0.36 | kept
- 20:40 | Claude | (same) | RESULT: the fix did NOT fix q108. The model quoted the Article 4 sentence ("... राज्य हो") as if it answered the question about the nation, the quote is really in the chunks (exact), so the check passed and q108 got the same wrong answer as v1. Retrieval misses answered "not found": 4/5 before, 4/5 after (same q016, q019, q020, q169). No previously answered question became "not found". 0 quotes failed the check (no invented quotes in v1 or v2 to catch) | kept as a negative result
- 20:40 | Claude | (same) | two more problems found: (1) q108 quote has the OCR typo "सार्वभीम" but the answer silently says "सार्वभौम"; (2) q111 quote covers only sub-clause (5), yet the answer adds the "तर सदस्यलाई अध्यक्षमा..." proviso from outside the quote. So the model does not stay inside its own quote, and the check (quote vs chunks) cannot see that | noted for write-up
- 20:41 | Claude | (same) | wrote results/fix_before_after.csv (label-free metrics now; "human-labeled correct" row pending my labels of results/labeling_v2.csv) | kept
- 20:41 | Claude | (same) | lesson: a prompt cannot fix a retrieval miss when a same-topic but wrong sentence is in the top 5; the model treats "related" as "answers". The root cause is retrieval/chunking (Article 3 merged into chunk o0001 because OCR read "राष्ट्र" as "राष्ट्ः"), which would need a chunking fix + 50 min BGE-M3 re-encode | noted
- 20:45 | me | what fix do you suggest now? | Claude checked the saved Step 3 results: BM25 finds 4 of BGE-M3's 5 misses at rank 1 (q016, q019, q020, q169 = exactly the 4 "not found" answers); at least one method finds the gold chunk for 175 of 177 questions. Suggested fix: hybrid retrieval (Reciprocal Rank Fusion of the saved BM25 + BGE-M3 top-5 lists): $0, minutes, no re-encode; test = Recall@5/MRR on the same 177 (BGE-M3 alone 0.966/0.848), then optionally re-answer the 30 (~$0.31) and label only changed answers. It will NOT fix q108 (both methods miss it). Also found 13 unsplit one-clause Article headings inside chunks (e.g. "राष्ट्ः" in o0001, "राष्ट्रभाषा" in o0003, "शपथ" in o0079), because the chunker only splits unnumbered headings followed by "(१)"; fixing that would fix q108 but needs a 50 min re-encode | pending my choice: (a) keep quote-first as the one Step 6 fix, hybrid = future work, or (b) run hybrid as a 2nd fix and report both
- 20:46 | me | go with (b): run hybrid retrieval as a 2nd fix and report both | kept
- 20:50 | Claude | (same) | wrote src/hybrid.py: Reciprocal Rank Fusion (K=60) of the SAVED Step 3 BM25 + BGE-M3 top-5 lists; no re-encode, no API, $0. Backup: log/retrieval_per_question.before-hybrid.csv. Outputs: "hybrid-rrf" rows in results/retrieval_per_question.csv, results/retrieval_metrics_hybrid.csv, results/fix2_before_after.csv | kept
- 20:50 | Claude | (same) | RESULT fix 2 (177 generated questions, same gold rule): Recall@5 0.966 -> 0.989, MRR 0.848 -> 0.883, misses 6 -> 2 (left: q031, q108, which BM25 also misses); baseline 5/5 at rank 1 stays 5/5. In the 30 labeling questions, q016, q019, q020, q169 are now retrieved (gold rank 0 -> 2, 3, 2, 3); q108 still missed; q120 and q130 move from rank 2 to 1 | kept
- 20:50 | Claude | (same) | note: fusion changes the top-5 set for 26 of the 30 labeling questions, so re-answering all 30 would need a full re-label; cheaper end-to-end check = re-answer only the 4 recovered questions (~$0.04, Sonnet, prompt ans-v1) and label 4 answers | pending my choice
- 20:48 | me | go: re-answer only the 4 recovered questions | kept
- 20:52 | Claude | (same) | added --hybrid-only to src/answer.py (backup log/answer.before-hybrid.py): same prompt ans-v1, same model, only the top 5 comes from hybrid-rrf; output results/labeling_hybrid.csv (with v1 answer, v1 label and old gold rank for reference; human_label empty). Dry run: 4 calls, 34,355 prompt chars, ~$0.05 | kept
- 20:50 | Claude (on my PC, C:\venvs\nre) | python src\answer.py --hybrid-only q016,q019,q020,q169 --model claude-sonnet-5-5 | 4 answers, no errors, served by claude-sonnet-5-5; 25,914 input + 405 output tokens = $0.056 | kept
- 20:50 | Claude | (same) | RESULT end-to-end: all 4 questions that were "not found" with BGE-M3 alone now get a real answer (gold chunk moved from outside the top 5 to rank 2-3). q016 "क्रमसंख्या १० मा", q020 and q169 match the reference wording; q019 matches and adds "तथा सर्वाङ्गीण राष्ट्रिय विकासमा प्रोत्साहन र परिचालन गर्न", which I must check against the source when labeling. results/labeling_hybrid.csv, human_label empty for me | pending my 4 labels
- 20:50 | Claude | (same) | Step 6 summary so far: fix 1 (quote-first prompt, $0.36) = no improvement; fix 2 (hybrid BM25 + BGE-M3 retrieval, $0 + $0.06) = Recall@5 0.966 -> 0.989, MRR 0.848 -> 0.883, misses 6 -> 2, 4 "not found" turned into answers. q108 (and q031) still missed by both methods: needs the chunking fix (13 unsplit one-clause headings) | kept
- 20:51 | me | chunking fix: add neighbouring chunks for more context ("first 3 and after 2") | Claude read it as: keep the top 3 retrieved chunks and add neighbour chunks around each (no re-chunking, no re-encode); measured both readings on the 177 questions from saved results, $0 | kept
- 20:53 | Claude | (same) | gold chunk inside the context the model would see: hybrid top 5 (now) 175/177 = 0.989, ~5 chunks / ~841 words; hybrid top 3 + 1 before/1 after 175/177, ~8 chunks / ~1,169 words (q108 fixed, q015 lost); hybrid top 3 + 3 before/2 after 176/177 = 0.994, ~14.6 chunks / ~2,050 words (q108 fixed, only q031 left). q108 is fixed because Article 4's chunk o0002 is in the top 3 and its neighbour before is o0001 (Article 3). Cost: ~2.4x more input tokens per answer | pending my choice + end-to-end check on q108
- 20:54 | me | go (re-answer q108 with top 3 + 3 before / 2 after); log everything | kept
- 20:56 | Claude | (same) | added --neighbors K,B,A to src/answer.py (backup log/answer.before-neighbors.py): with --hybrid-only, keep the hybrid top K chunks and add B chunks before and A after each, in document order; same prompt ans-v1, same model; output results/labeling_neighbors.csv. Dry run q108 with 3,3,2 | kept
- 20:57 | Claude (on my PC, C:\venvs\nre) | python src\answer.py --hybrid-only q108 --neighbors 3,3,2 --model claude-sonnet-5-5 | 1 call, no errors, served by claude-sonnet-5-5; 9,868 input + 209 output tokens = $0.02; context = 16 chunks and includes o0001 (Article 3) | kept
- 20:57 | Claude | (same) | RESULT: q108 now answers "नेपाली राष्ट्र बहुजातीय, बहुभाषिक, बहुधार्मिक, बहुसांस्कृतिक विशेषतायुक्त र भौगोलिक विविधतामा रहेको छ ..." (the 4 reference traits, plus the rest of the Article 3 definition); before: the Article 4 "राज्य" sentence (labeled wrong). results/labeling_neighbors.csv, human_label empty | pending my label
- 20:58 | Claude | (same) | wrote results/step6_fixes.csv: one row per fix (what changed, before, after, cost, result). Step 6 API spend: $0.36 + $0.06 + $0.02 = $0.44; total project API spend ~$2.86 | kept
- 20:58 | Claude | (same) | open for me: label results/labeling_v2.csv (30), labeling_hybrid.csv (4), labeling_neighbors.csv (1). Note for write-up: fixes 2 and 3 were tested only on the questions they changed (4 and 1), not on a full re-run of 30; directive-v3 said ONE fix, I chose to report all three honestly (fix 1 failed) | noted
- 21:00 | Claude | "also update finding" | updated findings.md (backup log/findings.before-step6.md): new finding 6 (3 Step 6 fixes with numbers), priority row 6, "Planned Step 6" line changed to future work (judge full-chunk fix not run), 3 Step 6 pricing rows; new total 185 calls, 414,570 in / 106,812 out, ≈ $2.87 (exact sum $2.865; earlier line said ~$2.86) | kept

## Entry #23: final-directive.md (plan vs what we actually did)
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 21:05 | Claude | compare the directives with what we actually did; write final-directive.md | read directive-v3 (v1/v2 changes already listed there), log Entries #5-#22, src/ and results/; wrote final-directive.md: rules and Steps 0-7 as actually built (Anthropic API, no temperature, Sonnet answers, Opus + Haiku judges, "not found" = wrong, three Step 6 fixes, C:\venvs\nre), actual file layout, a 17-row "Plan (v3) vs what we actually did" table with the reason and Entry # for each, known failures, total cost ≈ $2.87. v1-v3 untouched. Step 7 (Streamlit) and README marked not built yet | pending my review

## Entry #24: Step 7, Streamlit page
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 21:10 | Claude | simple Streamlit page: document → questions → Recall@5/MRR → judge agreement chart → failure examples | wrote app.py: reads only saved files (data/ocr, data/qa, results/), no API calls, no model download, no re-encode. Sections: 1 document (183 pages, 39,287 words, 311 chunks, 65 without Article number, chunk viewer), 2 questions (180 generated / 177 kept / 3 rejected with reason, type chart, sample), 3 retrieval (BM25, BGE-M3, hybrid Recall@5 + MRR chart, by type, baseline top-1), 4 judges (agreement + kappa chart, metrics table, human vs judge table), 5 failures (human wrong/not found rows, judge disagreements q111, Step 6 fixes table, q108 before/after) | kept
- 21:10 | Claude (cloud copy of my files) | test the page | ran with Streamlit's test runner: 0 errors, all numbers match the log; looked at screenshots. Changed the MRR display (Streamlit showed it with a green "up" arrow that meant nothing) | kept
- 21:10 | Claude | (same) | NOT run on my PC yet: pandas and streamlit still need installing into C:\venvs\nre. The question box from directive-v3 is left out (my request listed only these 5 sections) | pending me
- 21:11 | Claude (on my PC, C:\venvs\nre) | install pandas + streamlit and start the page | pip installed pandas 3.1.1, streamlit 1.67.0 (+ altair, pyarrow etc.), nothing else upgraded, no DLL/App Control block. First start hung on Streamlit's first-run "Email:" question; restarted with --server.showEmailPrompt false. http://localhost:8501 returns 200, no Python errors. Runs in the background (stop with Stop-Process -Id 6148). No API calls, app.py and data unchanged | kept, my click-through pending
- 21:18 | Claude | write the Streamlit info down in the project folder | saved STREAMLIT.md: what app.py shows, install, run, background run (email-prompt fix), stop | kept
- 21:20 | Claude | move the Streamlit app into src/ and tell me the command | moved app.py -> src/app.py (only change: ROOT = parent.parent so it still finds data/ and results/); STREAMLIT.md updated. Command from the project folder: C:\venvs\nre\Scripts\streamlit.exe run src\app.py. The background copy started at 21:11 used the old path, so it must be stopped and restarted | kept
- 21:21 | me | update everything in the log | Claude checked: Entries #21-#24 cover everything up to now (findings update, final-directive, Streamlit build, install, STREAMLIT.md, move to src/app.py) | kept
- 21:21 | Claude | status at 21:21 | DONE: Steps 1-7 built; findings.md (Steps 1-6); final-directive.md; src/app.py + STREAMLIT.md. OPEN for me: (1) stop the old background app (Stop-Process -Id 6148) and run `C:\venvs\nre\Scripts\streamlit.exe run src\app.py`, check all 5 sections for errors; (2) label results/labeling_v2.csv (30), labeling_hybrid.csv (4), labeling_neighbors.csv (1); (3) fill failure_type in results/disagreements.csv. OPEN for Claude after that: final-directive.md still says app.py at root and Step 7 "not built yet", so it needs a small update; README.md, write-up, videos not started. Total API spend ≈ $2.87 | noted

## Entry #25: README.md
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 21:22 | Claude | README: problem, how to run, results table, failures, step by step, also for people with their own PDF | read every script's usage/inputs/hard-coded paths, then wrote README.md: 1 problem, 2 folder map, 3 setup (Python 3.12 venv outside OneDrive, Tesseract + Poppler + nep.traineddata, .env), 4 run table + detail per step (commands, outputs, cost, time, human labeling rules), 5 own PDF (8 exact edits: PDF name in ocr.py, OCR check, own baseline-qa.md, page count + broken forms in ocr_quality.py, heading patterns in chunk_ocr.py, document name in 3 prompts, delete old outputs, dry runs), 6 results tables (document, retrieval, answers, judges, Step 6 fixes, cost ≈ $2.87), 7 nine failures/limitations, 8 how it was built. Step 6 labels marked pending. No code changed | pending my review

## Entry #26: 1-page write-up (draft)
**Date:** Nov 12, 2026

**Quick log (time | tool | what I asked | what happened | kept/rejected):**
- 21:25 | Claude | read intent.md, ai-log.md (only a header; my log is log/log.md) and findings.md; draft a 1-page write-up: problem, what I built, results, what failed, what I unlearned, how I used AI | saved writeup.md marked DRAFT (~800 words). "What I unlearned" = 5 points taken from logged events (Unicode PDF assumed clean; normalization expected as the fix; prompt can't fix retrieval; judges agreeing / my labels not automatically right; copy-paste vs page image) plus a placeholder for my own. Placeholders: Step 6 labels pending; Gemini vs "no AI" for baseline Q&A to confirm | pending my rewrite in my own words
- 21:26 | me | update log | Claude checked the log: Entries #23-#26 cover final-directive, Streamlit (build, install, STREAMLIT.md, move to src/app.py), README and the write-up draft. Fixed 2 wrong times: Entry #25 21:30 -> 21:22 and Entry #26 21:35 -> 21:25 (Claude had written times ahead of the real Nepal time; backup log/log.before-time-fix.md) | kept
- 21:26 | Claude | status | DONE: Steps 1-7, findings.md, final-directive.md, README.md, writeup.md (draft). OPEN for me: run src\app.py and check it; label Step 6 answers (labeling_v2 30, labeling_hybrid 4, labeling_neighbors 1); fill failure_type in disagreements.csv; rewrite writeup.md in my words + fill placeholders; Loom (≤5 min) + career video (≤5 min). OPEN for Claude: update final-directive.md Step 7 (now built, src/app.py) | noted
