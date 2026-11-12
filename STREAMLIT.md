# Streamlit page (Step 7)

**File:** `src/app.py`. It reads only saved files in `data/` and `results/`. No API calls, no model download, $0.

**What it shows (5 sections):**
1. Document: pages, words, chunks, chunk viewer
2. Questions: generated / kept / rejected, types, sample
3. Retrieval: Recall@5 and MRR for BM25, BGE-M3, hybrid (+ by type, baseline top-1)
4. Judges vs human: agreement + Cohen's kappa chart, human vs judge table
5. Failure examples: wrong / not found answers, judge disagreements (q111), Step 6 fixes, q108 before/after

## Install (once)
```
C:\venvs\nre\Scripts\python.exe -m pip install pandas streamlit
```
Installed on Nov 12, 2026: pandas 3.1.1, streamlit 1.67.0.

## Run
Open PowerShell in the project folder:
```
cd C:\Users\nepal\OneDrive\Desktop\nepali-rag-eval
C:\venvs\nre\Scripts\streamlit.exe run src\app.py
```
Then open http://localhost:8501. Stop with Ctrl+C.

If started in the background (no terminal), add `--server.showEmailPrompt false`, otherwise Streamlit waits forever on its first-run "Email:" question:
```
Start-Process C:\venvs\nre\Scripts\streamlit.exe -ArgumentList 'run','src\app.py','--server.showEmailPrompt','false' -WorkingDirectory 'C:\Users\nepal\OneDrive\Desktop\nepali-rag-eval'
```
Stop a background run: `Stop-Process -Name streamlit`

## Notes
- If a results file changes, refresh the page (or press "C" then "Rerun") to clear the cache.
- Step 6 answers are shown but not human-labeled yet.
