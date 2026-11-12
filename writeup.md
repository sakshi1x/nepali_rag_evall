# Measuring Nepali RAG on the Constitution of Nepal

## Project Overview

### The Problem

When a chatbot answers questions based on a Nepali document, how do we know its answers are correct and actually come from the document rather than the model's imagination?

I wanted to measure this across the entire RAG pipeline: extracting the text, retrieving the correct passages, and generating answers. I also wanted to find out whether an AI judge could evaluate answers as reliably as a careful human.

### What I Built

I built a small, reproducible evaluation setup using one source document: the Constitution of Nepal.

The project covered seven stages:

1. **OCR and Chunking:** Ran Tesseract with Nepali language support on all 183 pages. Checked the extracted text against the original page images and split the document into 311 Article-based chunks.

2. **Test Questions:** Used AI to generate 180 Nepali questions and filtered them down to 177. I also prepared 5 baseline questions myself.

3. **Retrieval Evaluation:** Compared BM25 and BGE-M3 using Recall@5 and Mean Reciprocal Rank (MRR).

4. **Answer Evaluation:** Manually labeled 30 answers. The labels were created without AI assistance.

5. **LLM-as-a-Judge Evaluation:** Compared two LLM judges against my manual labels using agreement, Cohen's kappa, and false-positive rates.

6. **Improvements:** Tested three changes, introducing one change at a time.

7. **Demo:** Built a small Streamlit application to demonstrate the system.

**Total API cost: approximately $2.87.**

### What I Found

#### 1. Retrieval Performance

On the AI-generated questions, BM25 and BGE-M3 performed almost equally.

| Metric | BM25 | BGE-M3 |
|---|---:|---:|
| Recall@5 | 0.955 | 0.966 |
| MRR | 0.862 | 0.848 |

However, the difference became more noticeable on my five manually written baseline questions.

- BGE-M3 ranked the correct passage first in all 5 cases.
- BM25 ranked the correct passage first in only 3 out of 5 cases.

This suggested that performance on generated questions alone might not tell the whole story.

#### 2. Answer Quality

I manually evaluated 30 answers:

| Result | Count |
|---|---:|
| Correct | 25 |
| Incorrect | 1 |
| Not found | 4 |
| **Total** | **30** |

All four "not found" cases were caused by retrieval misses rather than answer-generation failures.

#### 3. AI Judge Performance

I compared Opus 5.5 and Haiku 5.5 against my manually created labels.

Both judges produced identical verdicts:

- Agreement with my labels: 96.7%
- Cohen's kappa: 0.889
- False positives: 0 out of 5

Haiku cost approximately 1/34 as much as Opus.

For this evaluation task, the cheaper judge was sufficient. However, the results also showed that agreement between judges does not automatically guarantee correctness.

#### 4. Improvements and Fixes

I tested three improvements, changing one thing at a time.

- **Hybrid retrieval (BM25 + BGE-M3):** Improved Recall@5 from 0.966 to 0.989 and MRR from 0.848 to 0.883 without additional API cost. Retrieval misses dropped from 6 to 2, and all four "not found" questions received real answers when re-asked (about $0.06).
- **Neighbouring chunks:** Adding the 3 chunks before and 2 after each of the top 3 results put the correct passage in the model's context for 176 of 177 questions, at about 2.4 times the tokens. It fixed the confidently incorrect answer in q108.
- **Quote-first prompting:** Failed to solve the underlying problem. The model quoted a real sentence, but it was about the wrong subject.

The Step 6 answers (35 in total) have not yet been labeled by hand. These improvements are therefore measured by retrieval metrics and by reading the changed answers, not yet confirmed by full human labels. The hybrid and neighbour fixes were also re-run only on the questions they changed (4 and 1), not on all 30.

### What Went Wrong

This project exposed several problems that were not obvious at the beginning.

**1. The supposedly Unicode PDF was broken.**

The extracted PDF text was corrupted. The correct word `बमोजिम` appeared zero times, while the corrupted version `बमोजजम` appeared 712 times.

My first plan was to skip the broken text and use only the remaining usable content. However, that left just 0.4% of the original words.

I abandoned that approach and switched to OCR.

**2. OCR missed Article numbers printed in the margins.**

OCR detected 261 out of 308 Article headings. Some Articles were therefore merged into a single chunk.

This caused q108: the model confidently answered a question about the nation using the definition of the state from Article 4, instead of the relevant definition of the nation in Article 3.

**3. The quote-first prompt fix failed.**

The model successfully quoted an actual sentence from the document, but the sentence discussed the wrong subject.

A real quotation is not necessarily relevant evidence.

**4. Both judges rejected a correct answer.**

For q111, both judges incorrectly rejected a correct answer because they were given only one evidence sentence instead of the complete Article.

This showed how the amount of context provided to an AI judge can affect its verdict.

**5. My own labeling was not always correct.**

I made a labeling mistake on q108. Both judges caught it.

This was an important reminder that human labels are not automatically ground truth.

### What I Unlearned

These are some of the assumptions I had to reconsider while working through the project.

- **I thought the PDF already contained usable Unicode text.** I initially considered OCR outside the scope of the project. The text layer was actually corrupted, and OCR became one of the most important parts of the pipeline.

- **I expected Nepali language complexity to be the biggest challenge.** I thought word forms, numerals, dates, and normalization would cause most of the problems. In reality, the biggest failures came from extraction, chunking, and retrieval. I never ended up needing normalization.

- **I thought a stricter prompt would prevent incorrect answers.** It did not. A prompt cannot fix a retrieval miss. Providing better context did.

- **I assumed agreement between two AI judges meant they were probably right.** Both judges agreed with each other and still incorrectly rejected q111. They also correctly identified my labeling mistake on q108.

- **I assumed copied or AI-retyped text was reliable enough to use as a source.** Small spelling changes went unnoticed and silently corrupted the data. I learned to treat the original page image as the source of truth.

- **I thought I would always notice a wrong answer.** What surprised me most personally was q108. I first labeled it correct myself, because it was fluent and used the Constitution's own words. Only when both judges disagreed did I go back to Article 3 and see that the answer came from the wrong Article. If a plausible answer could fool me while I was carefully checking, it can easily fool a real user. That is exactly why measuring matters more than trusting how an answer sounds.

### How I Used AI

I used Claude as a coding agent, following written instructions throughout the project.

I revised those instructions only after encountering actual failures:

- v1: Initial project instructions.
- v2: Revised instructions after discovering the OCR problem.
- v3: Updated instructions for the quotation and Article-heading fixes.
- Final version: The instructions as actually followed, with a plan-versus-actual table that links every change to a logged event.

Claude worked one step at a time, showed me the estimated cost before every paid API run, and logged everything, including rejected outputs, in `log/log.md`.

The log contains 25 entries.

Claude also interviewed me to help draft `intent.md`.

For the baseline question-and-answer pairs, I used Gemini Notebook to help write the five pairs.

**Models used:**

| Task | Model |
|---|---|
| Question generation | Opus 5.5 |
| Answer generation | Sonnet 5.5 |
| Answer judging | Opus 5.5 |
| Answer judging | Haiku 5.5 |

### What I Kept Under My Control

I did not hand over the important evaluation decisions to AI.

I personally handled:

- All 30 manual answer labels.
- Decisions about the project scope and model selection.
- Choosing OCR after discovering the broken PDF text layer.
- Selecting a cheaper answer-generation model.
- Deciding to count "not found" answers as incorrect.
- Choosing which improvements to test.
- Rechecking disputed answers against the original Constitution.

### What I Rejected

Not every AI-generated suggestion or approach made it into the final system.

I rejected:

- The initial plan to skip the broken PDF text.
- Using Opus for answer generation because of its higher cost.
- AI-retyped quotations as reliable source text.
- The quote-first prompting fix after it failed to address the actual problem.

### Final Takeaway

The biggest lesson from this project was that RAG quality is not just about choosing a better language model.

A system can generate fluent Nepali answers and still fail because the original document was extracted incorrectly, Articles were merged during chunking, or retrieval returned the wrong evidence.

Likewise, two AI judges can agree and still be wrong.

The most valuable improvements came from checking the original document, identifying where the pipeline actually failed, and fixing those failures rather than simply making the prompts stricter or choosing a larger model.

This project gave me a way to measure those problems instead of relying on answers that merely looked convincing.
