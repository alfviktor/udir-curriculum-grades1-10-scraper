# Udir Curriculum G1‑10 Scraper

> Download, rename and stage the Norwegian LK20 curriculum PDFs (grades 1‑10) as reproducible data files.

This repository contains a small, config‑driven Python tool that will

* fetch the official **LK20** curriculum PDFs from the Norwegian Directorate for Education and Training (Udir),
* save them under `data/raw_pdfs/`,
* normalise the filenames to human‑readable subject names in `data/processed/`, and
* expose helper utilities for further parsing (e.g. PDF metadata extraction).

The source subjects and their codes live in `config/subjects.json`; simply edit this file to change which curricula are downloaded.

---

## Project status

The scraper is intentionally lightweight and opinionated—perfect if you just need the raw PDF documents in a tidy folder.  Pull requests adding
metadata parsing, alternate formats (HTML, DOCX) or better test coverage
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
$ git clone https://github.com/<your-user>/udir-curriculum-g1-10-scraper.git
$ cd udir-curriculum-g1-10-scraper

# 2. Create a virtual environment (recommended)
$ python -m venv .venv
$ source .venv/bin/activate

# 3. Install requirements
$ pip install -r requirements.txt

# 4. Run the scraper (downloads ~20–30 MB)
$ python -m src.scraper
```

On completion you should see:

```text
Attempting 11 curriculum PDFs
100%|████████████████████████████| 11/11 [00:18<00:00,  1.64s/it]
Download & processing complete.
```

All curriculum PDFs will now be located in `data/processed/` with readable names, e.g. `Mathematics_G1-10.pdf`.

### CLI options

Currently there are no CLI flags; edit `config/subjects.json` and rerun the script if you need a different subset.

---

## Directory structure

```text
.
├── config/                 # Subject‑code → name map (JSON)
├── data/
│   ├── processed/          # Final PDFs with standardised names
│   └── raw_pdfs/           # Original downloads, untouched
├── logs/                   # scrape_errors.log + future logs
├── src/
│   ├── scraper.py          # Entrypoint script
│   └── utilities.py        # Helper functions & path constants
├── requirements.txt
└── README.md
```

---

## Configuration

`config/subjects.json` maps subject codes (e.g. `MAT01-05`) to target filenames. To scrape more or fewer curricula, delete or add entries.  No code changes are required as the scraper builds URLs dynamically.

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

* **Source**: `https://www.udir.no/lk20/` (LK20 curriculum portal)
* **Grade range**: 1 – 10 (primary + lower secondary)
* **Terms of use**: The PDFs are published under the Norwegian Licence for Open Government Data (NLOD). Always verify with Udir if you redistribute.

This repository’s **code** is released under the MIT licence—see `LICENSE` for full text.  The curriculum PDFs themselves remain the intellectual property of Udir and are **not** included in the repo; the scraper merely automates their retrieval.

---

## Contributing

Contributions are welcome via pull request.  Please:

1. Open an issue first if it’s a major change.
2. Follow PEP 8 + ruff guidelines.
3. Ensure the scraper still runs successfully (`python -m src.scraper`).

---

## Disclaimer

This project is **unofficial** and not endorsed by Udir.  Use responsibly:

* Requests are throttled (`REQUEST_DELAY = 1.5 s`) to stay polite—keep it.
* Review Udir’s robots.txt and terms before heavy usage.
* If you publish derivative data, attribute the original source.
"
