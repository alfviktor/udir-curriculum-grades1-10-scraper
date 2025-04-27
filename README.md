# TakeoverPod Transcript Scraper

> Gather, clean, and store episode transcripts from the TakeoverPod website (`https://www.takeoverpod.com/episodes`) for analysis and indexing.

This repository contains a Python tool that will:

* fetch episode pages from `https://www.takeoverpod.com/episodes`,
* extract the transcript text using the selector:
  `body > ... > section.section_transcript > div > div`,
* clean and normalize the transcript text,
* split the text into manageable chunks (<= 512 tokens),
* save the raw HTML, cleaned transcripts, and chunked data to disk.

---

## Project status

The scraper is currently being refactored from a previous project. It aims to provide a clean pipeline for acquiring TakeoverPod transcripts. Contributions for improved text cleaning, error handling, or testing are welcome.

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
# 1. Clone (assuming you've renamed the repo or are working locally)
$ git clone https://github.com/<your-user>/takeoverpod-scraper.git
$ cd takeoverpod-scraper

# 2. Create a virtual environment (recommended)
$ python -m venv .venv
$ source .venv/bin/activate

# 3. Install requirements (Update requirements.txt first!)
$ pip install -r requirements.txt

# 4. Run the scraper
$ python -m src.podcast_scraper # Note: Entry point might change
```

On completion, you should see log messages indicating successful scraping and processing. All data will be located in the `episodes/` directory.

### CLI options

Currently, there are no command-line options planned. The base URL is hardcoded.

---

## Directory structure

```text
.
├── episodes/
│   ├── raw_html/       # Original downloaded HTML episode pages
│   ├── transcripts/    # Cleaned transcript text files
│   └── chunks.jsonl    # Chunked transcript data for indexing
├── logs/
│   └── scrape_errors.log # Log file for errors during scraping
├── src/
│   ├── podcast_scraper.py # Main entrypoint script (TBC)
│   └── utilities.py     # Helper functions (TBC)
├── requirements.txt     # Project dependencies
└── README.md          # This file
```

---

## Configuration

There is no separate configuration file. The target URL (`https://www.takeoverpod.com/episodes`) and the transcript DOM selector are defined within the source code.

### Output structure (`chunks.jsonl`)

Each line in `chunks.jsonl` will be a JSON object, likely containing fields like: `{ "episode_url": "...", "title": "...", "chunk_index": 0, "text": "...", "tokens": 123 }` (Exact fields TBC).

### Tech overview

| Step | Tool | Description |
|---|---|---|
| URL discovery | `aiohttp`, `BeautifulSoup` | Find episode links on the main page |
| Download | `aiohttp` | Fetch HTML content asynchronously |
| Parse | `BeautifulSoup` | Extract transcript using DOM selector |
| Clean | Python | Remove HTML, normalize whitespace, etc. |
| Chunk | Custom splitter | Split text into ~512 token chunks |
| Store | File I/O | Save raw HTML, plain text, JSON Lines |

See `tech_doc.md` for more details.

---

## Development

Formatting/linting is handled by **ruff**. Adding tests with **pytest** is encouraged.

```bash
# Lint
ruff check src/

# Run tests (once tests/ are added)
pytest -q
```

---

## Data source and licence

* **Source**: [TakeoverPod Episodes](https://www.takeoverpod.com/episodes)
* **Terms of use**: The transcript content belongs to the creators of TakeoverPod. Please respect their terms of use and intellectual property. This scraper is for personal or analytical use; ensure compliance before redistributing any scraped data.

This repository’s **code** is released under the MIT licence. The scraped **content** remains the property of TakeoverPod.

---

## Contributing

Contributions are welcome via pull request. Please:

1. Open an issue first if it’s a major change.
2. Follow PEP 8 + ruff guidelines.
3. Ensure the scraper runs successfully (e.g., `python -m src.podcast_scraper`).

---

## Disclaimer

This project is **unofficial** and not endorsed by TakeoverPod. Use responsibly:

* Requests should be throttled (e.g., `REQUEST_DELAY = 1.5 s`) to be respectful to the website.
* Review the website's `robots.txt` and terms of service.
* If you use the scraped data, consider attributing the original source.
