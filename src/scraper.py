"""Main LK20 PDF Scraper."""
from __future__ import annotations

import time
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from PyPDF2 import PdfReader

from dotenv import load_dotenv
import os

load_dotenv()

from src.utilities import RAW_DIR, PROCESSED_DIR, load_subject_map, log_error
from src.s3_upload import upload_directory

BASE_URL = "https://data.udir.no/kl06/v201906/laereplaner-lk20/"
ROOT_PAGE = "https://www.udir.no/lk20/"  # no longer used
REQUEST_DELAY = 1.5  # seconds
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LK20Scraper/1.0; +https://github.com/yourusername)"
}

def throttled_get(url: str, **kwargs):
    time.sleep(REQUEST_DELAY)
    return requests.get(url, headers=HEADERS, **kwargs)

def build_pdf_links():
    """Construct PDF URLs from subject codes in config."""
    codes = load_subject_map().keys()
    return [f"{BASE_URL}{code}.pdf" for code in codes]

def download_pdf(url: str, retries: int = 3) -> bool:
    for attempt in range(1, retries + 1):
        try:
            r = throttled_get(url, stream=True, timeout=15)
            r.raise_for_status()
            filename = url.split("/")[-1].split("?")[0]
            target = RAW_DIR / filename
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            log_error(f"Attempt {attempt} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    return False

def standardize_filenames():
    mapping = load_subject_map()
    for pdf in RAW_DIR.glob("*.pdf"):
        code = pdf.stem.split("_")[0]
        new_name = mapping.get(code, code) + ".pdf"
        pdf.rename(PROCESSED_DIR / new_name)

def extract_metadata(pdf_path: Path):
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        return reader.metadata

def main():
    pdf_links = build_pdf_links()
    print(f"Attempting {len(pdf_links)} curriculum PDFs")
    with tqdm(total=len(pdf_links)) as bar:
        for url in pdf_links:
            if download_pdf(url):
                bar.update(1)
            else:
                log_error(f"Failed permanently: {url}")
    standardize_filenames()
    print("Download & processing complete.")
    # Automatically upload processed PDFs to S3
    bucket = os.getenv("AWS_S3_BUCKET")
    prefix = os.getenv("AWS_S3_PREFIX", "")
    if bucket:
        print(f"Uploading processed PDFs to S3 bucket {bucket}/{prefix}")
        upload_directory(bucket, prefix)
    else:
        print("No AWS_S3_BUCKET env var set; skipping S3 upload.")

if __name__ == "__main__":
    main()
