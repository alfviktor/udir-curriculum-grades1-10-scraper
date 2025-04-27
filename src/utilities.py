"""Utility helpers for bank scraping."""
from pathlib import Path
import json
import logging
import re
from typing import Dict, List, Optional

# --- Project directories ---------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure common directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Legacy directories kept for backward-compatibility with LK20 scraper
RAW_DIR = DATA_DIR / "raw_pdfs"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# --- Logging ---------------------------------------------------------------
logging.basicConfig(
    filename=LOGS_DIR / "bank_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- HTTP headers ----------------------------------------------------------
HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BankPageScraper/1.0; "
        "+https://github.com/alfviktor/lokalbank-info-scraper)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nb,no;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

# --- Helper functions ------------------------------------------------------

def log_error(message: str) -> None:
    """Log error message to file and stderr."""
    logging.error(message)
    print(f"ERROR: {message}")


def log_info(message: str) -> None:
    """Log info-level message to file and stdout."""
    logging.info(message)
    print(message)


# ---------------------------------------------------------------------------
# Bank-specific helpers
# ---------------------------------------------------------------------------

def setup_bank_directories(bank_name: str) -> Dict[str, Path]:
    """Create and return all paths for a given bank."""
    bank_dir = DATA_DIR / bank_name.lower()
    raw_html_dir = bank_dir / "raw_html"
    raw_pdf_dir = bank_dir / "raw_pdf"
    chunks_file = bank_dir / "chunks.jsonl"

    # Ensure they exist
    raw_html_dir.mkdir(parents=True, exist_ok=True)
    raw_pdf_dir.mkdir(parents=True, exist_ok=True)
    if not chunks_file.exists():
        chunks_file.touch()

    return {
        "bank_dir": bank_dir,
        "raw_html": raw_html_dir,
        "raw_pdf": raw_pdf_dir,
        "chunks_file": chunks_file,
    }


def sanitize_filename(url: str) -> str:
    """Convert an URL to a filesystem-safe filename (without extension)."""
    filename = re.sub(r"^https?://", "", url)
    filename = filename.split("?")[0]  # strip query string
    filename = filename.rstrip("/")
    filename = filename.replace("/", "-")
    filename = re.sub(r"[\\*?:\"<>|]", "_", filename)
    return filename[:150]  # safety truncate


# ------------------------- text chunking -----------------------------------

def _simple_tokenize(txt: str) -> List[str]:
    return re.findall(r"\w+|[^\w\s]", txt)


def chunk_text(text: str, title: Optional[str] = None, max_tokens: int = 512) -> List[Dict]:
    """Split *text* into ~max_tokens chunks preserving paragraphs."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[Dict] = []

    cur_lines: List[str] = []
    cur_tokens = 0

    def _flush():
        nonlocal cur_lines, cur_tokens
        if cur_lines:
            body = " ".join(cur_lines)
            if title and not body.startswith(title):
                body = f"{title}: {body}"
            chunks.append({"text": body, "tokens": cur_tokens})
            cur_lines = []
            cur_tokens = 0

    for para in paragraphs:
        tokens = len(_simple_tokenize(para))
        if tokens > max_tokens:
            # split paragraph too long
            words = para.split()
            seg: List[str] = []
            seg_tokens = 0
            for w in words:
                w_tokens = len(_simple_tokenize(w))
                if seg_tokens + w_tokens > max_tokens:
                    cur_lines.append(" ".join(seg))
                    cur_tokens += seg_tokens
                    _flush()
                    seg, seg_tokens = [], 0
                seg.append(w)
                seg_tokens += w_tokens
            if seg:
                cur_lines.append(" ".join(seg))
                cur_tokens += seg_tokens
                _flush()
            continue
        if cur_tokens + tokens > max_tokens:
            _flush()
        cur_lines.append(para)
        cur_tokens += tokens
    _flush()
    return chunks


# ---------------------------------------------------------------------------
# Legacy function kept to avoid breaking lk20 scraper (not used by banks)
# ---------------------------------------------------------------------------

def load_subject_map() -> dict:
    """Load subject code -> name mapping (legacy)."""
    cfg_path = CONFIG_DIR / "subjects.json"
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
