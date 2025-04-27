import json
import re
from datetime import datetime
from pathlib import Path
import argparse

TITLE_RE = re.compile(r"^TITLE:\s*(.+?)$", re.IGNORECASE)
URL_RE = re.compile(r"^URL:\s*(.+?)$", re.IGNORECASE)


def extract_info(txt_path: Path):
    """Extract title and URL from processed txt file."""
    title = txt_path.stem  # fallback
    url = ""
    with txt_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not title:
                m = TITLE_RE.match(line.strip())
                if m:
                    title = m.group(1).strip()
                    continue
            m = URL_RE.match(line.strip())
            if m:
                url = m.group(1).strip()
                break  # we have what we need
            if line.strip() == "CONTENT:" or line.strip().startswith("CONTENT:"):
                break  # reached content section without url found
    return title, url


def generate_metadata(processed_dir: Path, bank_name: str, scope: str = "bank_info"):
    txt_files = list(processed_dir.glob("*.txt"))
    print(f"Found {len(txt_files)} .txt files in {processed_dir}")
    for txt_file in txt_files:
        meta_path = txt_file.with_suffix(".metadata.json")
        if meta_path.exists():
            continue  # skip existing
        title, url = extract_info(txt_file)
        metadata = {
            "title": title,
            "source_url": url,
            "bank_name": bank_name,
            "scope": scope,
            "doc_type": "pdf" if url.lower().endswith(".pdf") else "webpage",
            "extraction_date": datetime.utcnow().isoformat(),
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"Created {meta_path.relative_to(processed_dir.parent)}")


def main():
    parser = argparse.ArgumentParser(description="Generate metadata JSON for processed txt files.")
    parser.add_argument("bank_dir", type=str, help="Path to bank directory, e.g., data/flekkefjord")
    args = parser.parse_args()

    bank_dir = Path(args.bank_dir)
    processed_dir = bank_dir / "processed"
    if not processed_dir.is_dir():
        raise SystemExit(f"Processed directory not found: {processed_dir}")
    bank_name = bank_dir.name  # use directory name as bank name
    generate_metadata(processed_dir, bank_name)


if __name__ == "__main__":
    main()
