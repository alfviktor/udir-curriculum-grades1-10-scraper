"""Utility helpers for LK20 PDF scraper."""
from pathlib import Path
import json
import logging

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw_pdfs"
PROCESSED_DIR = DATA_DIR / "processed"
CONFIG_DIR = ROOT_DIR / "config"
LOGS_DIR = ROOT_DIR / "logs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOGS_DIR / "scrape_errors.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def load_subject_map() -> dict:
    """Load subject code -> name mapping from config/subjects.json"""
    with open(CONFIG_DIR / "subjects.json", "r", encoding="utf-8") as f:
        return json.load(f)


def log_error(message: str):
    logging.error(message)
    print(message)
