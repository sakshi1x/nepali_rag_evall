# Intent: Nepali Document Q&A Evaluation

## 1. Problem
When a chatbot answers questions from a Nepali document, nobody really knows whether its answers are correct and grounded in the source. I want to measure this instead of assuming it, across the whole pipeline: text extraction, embeddings, retrieval and answer generation.

I also want to find out whether an AI judge can reliably grade these answers. To check that, I will compare its grades against my own human labels.

## 2. Who has this problem
- **Nepali chatbot developers** building RAG systems. They need to know whether their embedding model finds the right passage and whether the answer is correct.
- **Organizations and researchers** who want their Nepali documents to be searchable through AI Q&A, but need confidence that the answers are accurate.

## 3. Why it is hard in Nepali
These are the challenges I expect. Part of this project is checking which ones actually show up.

- **Word forms:** One root word has many forms (गर्न, गरेको, गर्दैछ, गर्नुभयो). Keyword search and tokenizers may not see that they share a meaning.
- **Flexible phrasing:** Word order and honorifics change, but the meaning stays the same. Retrieval has to match meaning, not exact words.
- **Text quality:** Devanagari extraction can produce Unicode problems, broken half-letters (halanta) and irregular spacing. Nepali numerals (२७५) and English numerals (275) mean the same thing but don't match as text.
- **Dates:** The Constitution uses Bikram Sambat dates (२०७२ असोज ३), while users or models may use Gregorian dates.
- **Low-resource language:** There are few human-labeled Nepali Q&A datasets, so there is little to benchmark against. That is why I have to build and label my own test set.

## 4. Success by Nov 15
1. Extract and chunk the Nepali Constitution PDF.
2. Auto-generate a Q&A test set with AI, then filter out bad questions.
3. Compare BM25 (keyword) and BGE-M3 (embedding) retrieval using Recall@5 and MRR.
4. Generate answers, and hand-label 30 of them myself as correct or wrong.
5. Run 2 LLM judges and compare them with my labels: agreement %, Cohen's kappa, false-positive rate and the types of failure.
6. Try one fix (for example, Nepali/English numeral or date normalization) and compare results before and after.
7. Build a simple Streamlit demo where you can ask a question and see the retrieved passages and the answer.

I don't have target numbers yet. I will measure a baseline first and judge the results against it.

## 5. Out of scope
- Training or fine-tuning any model.
- Languages other than Nepali.
- More than one document. Only the Constitution of Nepal is used.
- Scanned PDFs, OCR and Preeti-font conversion. My PDF is already Unicode text.
- More than 30 human labels or more than 2 judges.

## Workflow
Constitution PDF → extract and chunk → generate and filter Q&A → retrieval (BM25 vs BGE-M3) → answer generation → human labels (30) → LLM judges vs labels → one fix → demo

**Core objective:** Measure, rather than assume, whether Nepali retrieval and answers are correct, and whether an AI judge can be trusted to grade them.
