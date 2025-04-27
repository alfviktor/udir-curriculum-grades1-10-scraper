# Purpose
This codebase is designed to automate the scraping, processing, and storage of podcast episode transcripts from the TakeoverPod website (https://www.takeoverpod.com/episodes). By building a reliable pipeline for transcript retrieval and preparation, we can support tasks such as vector indexing, search, and analysis of podcast content without manual intervention.

---
## 1. Goals
* Collect publicly available episode pages and extract their transcripts.
* Parse the transcript content embedded in the page via the DOM selector:
  `document.querySelector("body > div > main > div > div > div.page-right.is-template-page-episode > section.section_transcript > div > div")`.
* Clean and normalize text for consistency (remove HTML, speaker labels, timestamps).
* Split transcripts into manageable token-limited chunks for downstream processing.
* Store the prepared data in JSON Lines format for easy ingestion by vector databases.

---
## 2. High-Level Steps
| Step | Description | Tooling |
|---|---|---|
| 1 | Discover episode URLs | `aiohttp`, BeautifulSoup |
| 2 | Fetch episode HTML | asynchronous HTTP client (`aiohttp`) |
| 3 | Extract raw transcript | DOM parsing via BeautifulSoup |
| 4 | Clean & normalize text | Python string operations |
| 5 | Chunk text | custom splitter (≤512 tokens) |
| 6 | Save output | JSON Lines (`.jsonl`) |

---
## 3. Directory Structure
```
episodes/
  raw_html/           # Original downloaded HTML pages
  transcripts/        # Cleaned transcript text files
  chunks.jsonl        # Tokenized chunks ready for indexing
```

---
## 4. Compliance
* Only public pages are accessed — no login or private endpoints.
* Respect `robots.txt` and throttle requests (e.g., 1.5 s delay) to avoid overloading the server.
* Store source URL metadata for traceability in downstream applications.

---
_Rev. 27 Apr 2025 – Alf Viktor_