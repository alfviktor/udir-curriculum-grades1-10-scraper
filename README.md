# Bank Information Scraper

> Gather public customer & product info from Norwegian local banks (HTML pages + PDFs) for demo-chat indexing.

This repository contains a small, config‑driven Python tool that will

* fetch the official **bank information** from Norwegian local banks,
* save them under `data/raw_html/` and `data/raw_pdf/`,
* normalise the filenames to human‑readable names in `data/processed/`, and
* expose helper utilities for further parsing (e.g. HTML metadata extraction).

The source banks and their codes live in `config/banks.json`; simply edit this file to change which banks are scraped.

---

## Project status

The scraper is intentionally lightweight and opinionated—perfect if you just need the raw HTML and PDF documents in a tidy folder.  Pull requests adding
metadata parsing, alternate formats (DOCX) or better test coverage
are very welcome!

---

## Table of contents

1. [Quick start](#quick-start)
2. [Directory structure](#directory-structure)
3. [Configuration](#configuration)
4. [Development](#development)
5. [Data source and licence](#data-source-and-licence)
6. [Contributing](#contributing)

---

## Quick start

```bash
# 1. Clone
$ git clone https://github.com/<your-user>/bank-information-scraper.git
$ cd bank-information-scraper

# 2. Create a virtual environment (recommended)
$ python -m venv .venv
$ source .venv/bin/activate

# 3. Install requirements
$ pip install -r requirements.txt

# 4. Run the scraper (downloads ~20–30 MB)
$ python -m src.bank_scraper
```

On completion you should see:

```text
Attempting 11 bank pages
100%|████████████████████████████| 11/11 [00:18<00:00,  1.64s/it]
Download & processing complete.
```

All bank information will now be located in `data/processed/` with readable names, e.g. `flekkefjord/raw_html/` and `flekkefjord/raw_pdf/`.

### CLI options

Currently there are no CLI flags; edit `config/banks.json` and rerun the script if you need a different subset.

---

## Directory structure

```text
.
├── config/                 # Bank‑code → name map (JSON)
├── data/
│   ├── processed/          # Final HTML and PDF files with standardised names
│   └── raw_html/           # Original HTML downloads, untouched
│   └── raw_pdf/            # Original PDF downloads, untouched
├── logs/                   # scrape_errors.log + future logs
├── src/
│   ├── bank_scraper.py     # Entrypoint script
│   └── utilities.py        # Helper functions & path constants
├── requirements.txt
└── README.md
```

---

## Configuration

`config/banks.json` maps bank codes (e.g. `flekkefjord`) to target filenames. To scrape more or fewer banks, delete or add entries.  No code changes are required as the scraper builds URLs dynamically.

```json
{
  "flekkefjord": "flekkefjordsparebank.no",
  "valle": "valle-sparekasse.no"
}
```

### Output structure

```
data/
  flekkefjord/
    raw_html/
    raw_pdf/
    chunks.jsonl
```

Each `chunks.jsonl` line: `{bank, url, title, chunk, tokens}`

### Tech overview

| Step | Tool |
|---|---|
| URL discovery | `sitemap.xml` / `robots.txt` |
| Download | `aiohttp` (max 8 concurrent) |
| Parse | BeautifulSoup & pdfminer.six |
| Chunk | 512-token splitter |
| Store | JSON Lines |

See `tech_doc.md` for full spec.

---

## Development

Formatting/linting is handled by **ruff**, and a minimal test suite can be added with **pytest**.  Feel free to open an issue or PR if you encounter problems.

```bash
# Lint
ruff check src/

# (Optional) run tests once tests/ is added
pytest -q
```

---

## Data source and licence

* **Source**: Various Norwegian local banks
* **Terms of use**: The HTML and PDF pages are published under the Norwegian Licence for Open Government Data (NLOD). Always verify with the bank if you redistribute.

This repository’s **code** is released under the MIT licence—see `LICENSE` for full text.  The bank information themselves remain the intellectual property of the banks and are **not** included in the repo; the scraper merely automates their retrieval.

---

## Contributing

Contributions are welcome via pull request.  Please:

1. Open an issue first if it’s a major change.
2. Follow PEP 8 + ruff guidelines.
3. Ensure the scraper still runs successfully (`python -m src.bank_scraper`).

---

## Disclaimer

This project is **unofficial** and not endorsed by any bank.  Use responsibly:

* Requests are throttled (`REQUEST_DELAY = 1.5 s`) to stay polite—keep it.
* Review the bank’s robots.txt and terms before heavy usage.
* If you publish derivative data, attribute the original source.
