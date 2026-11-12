"""OCR the Constitution PDF page images with Tesseract (Nepali).
The PDF's own text layer is corrupted, but the pages LOOK correct, so we read the images.
Needs: pdftoppm (poppler), tesseract, and assets/ocr/nep.traineddata.
Usage:  python src/ocr.py --pages 1-3      (test)
        python src/ocr.py                  (all pages; resumes, skips pages already done)
Output: data/ocr/pages_ocr.jsonl   ({"page", "text"}). Original data/processed/ is not touched.
Each page image is deleted right after OCR, and the temp folder is removed at the end."""
import argparse, json, shutil, subprocess, tempfile, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF = sorted((ROOT / "assets").glob("*mtbuyjt.pdf"))[0]
TESSDATA = ROOT / "assets" / "ocr"
OUT = ROOT / "data" / "ocr" / "pages_ocr.jsonl"
DPI = 300


def n_pages():
    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout
    return int(next(l.split()[-1] for l in info.splitlines() if l.startswith("Pages:")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", help="range like 1-3")
    ap.add_argument("--part", default="", help="suffix for a parallel run, e.g. a -> pages_ocr_a.jsonl")
    args = ap.parse_args()
    total = n_pages()
    first, last = (map(int, args.pages.split("-")) if args.pages else (1, total))

    out = OUT.with_name(f"pages_ocr_{args.part}.jsonl") if args.part else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    for f_ in OUT.parent.glob("pages_ocr*.jsonl"):  # skip pages done by any run
        done |= {json.loads(l)["page"] for l in f_.open(encoding="utf-8")}

    tmp = Path(tempfile.mkdtemp(prefix="ocr_"))
    try:
        with out.open("a", encoding="utf-8") as f:
            for p in range(first, last + 1):
                if p in done:
                    continue
                img_prefix = tmp / f"p{p}"
                subprocess.run(["pdftoppm", "-r", str(DPI), "-gray", "-png", "-f", str(p), "-l", str(p),
                                "-singlefile", str(PDF), str(img_prefix)], check=True)
                img = img_prefix.with_suffix(".png")
                txt = subprocess.run(["tesseract", str(img), "stdout", "-l", "nep", "--tessdata-dir", str(TESSDATA)],
                                     capture_output=True, text=True, check=True).stdout
                img.unlink()  # free space immediately
                f.write(json.dumps({"page": p, "text": unicodedata.normalize("NFC", txt)}, ensure_ascii=False) + "\n")
                f.flush()
                print(f"page {p} done", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # remove temp folder


if __name__ == "__main__":
    main()
