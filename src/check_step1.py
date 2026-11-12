"""Step 1 checks: counts, chunk lengths, article coverage, baseline quotes, broken-text signs."""
import json, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
chunks = [json.loads(l) for l in (ROOT / "data/processed/chunks.jsonl").open(encoding="utf-8")]
pages = [json.loads(l) for l in (ROOT / "data/processed/pages.jsonl").open(encoding="utf-8")]
D2A = str.maketrans("०१२३४५६७८९", "0123456789")

print("pages:", len(pages), " chunks:", len(chunks))
lens = sorted(len(c["text"].split()) for c in chunks)
print("words per chunk  min/avg/max:", lens[0], sum(lens) // len(lens), lens[-1])

nums = [int(c["article"].translate(D2A)) for c in chunks if c["article"] and c["part"] == 0]
print("article headings found:", len(nums), " unique:", len(set(nums)))
missing = sorted(set(range(1, 309)) - set(nums))
print("articles 1-308 missing:", len(missing), missing[:30])
dups = sorted({n for n in nums if nums.count(n) > 1})
print("numbers seen more than once (likely schedule items, not articles):", dups[:30])

print("\n--- baseline-qa.md evidence quotes found in chunks? ---")
base = (ROOT / "baseline-qa.md").read_text(encoding="utf-8")
quotes = re.findall(r'\*\*Evidence from text:\*\*\s*"(.+?)"', base)
alltext = " ".join(c["text"] for c in chunks)
for q in quotes:
    q2 = " ".join(q.split())
    print("FOUND " if q2 in alltext else "MISSING", q2[:70])

print("\n--- signs of a broken text layer (correct form vs broken form) ---")
for good, bad in [("बमोजिम", "बमोजजम"), ("हुनेछ", "िुनेछ"), ("रहनेछ", "रिनेछ"),
                  ("गर्न", "गनव"), ("कार्य", "कायव"), ("प्रतिनिधि", "प्रमिमनमध"), ("देवनागरी", "देिनागरी")]:
    print(f"{good}: {alltext.count(good):4d}   {bad}: {alltext.count(bad):4d}")

random.seed(42)
print("\n--- 3 random chunks (read these yourself) ---")
for c in random.sample(chunks, 3):
    print(f"\n[{c['chunk_id']}] article {c['article']} '{c['title']}' page {c['page']}\n{c['text'][:400]}")
