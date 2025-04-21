
<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# Execute on the issue above and make a step by step program implementation guide

Here's a comprehensive technical implementation guide to systematically download all LK20 PDFs for grades 1-10:

# Comprehensive Guide to Scraping LK20 Curriculum PDFs

## 1. System Requirements \& Setup

### 1.1 Software Prerequisites

- **Python 3.10+** (with pip package manager)
- Required libraries:

```bash
pip install requests beautifulsoup4 tqdm python-dotenv
```

- **Git** (for version control)
- **7-Zip** (for archive management)


### 1.2 Directory Structure

```python
lk20_scraper/
├── config/
│   └── subjects.json    # Subject code registry
├── data/
│   ├── raw_pdfs/        # Original downloads
│   └── processed/       # Renamed files
├── logs/
│   └── scrape_errors.log
└── src/
    ├── scraper.py       # Main script
    └── utilities.py     # Helper functions
```


## 2. Technical Implementation

### 2.1 Base URL Identification

```python
BASE_URL = "https://data.udir.no/kl06/v201906/laereplaner-lk20/"
ROOT_PAGE = "https://www.udir.no/lk20/"
```


### 2.2 Web Scraping Logic

```python
def extract_pdf_links():
    """Identifies all PDF links from Udir's curriculum pages"""
    response = requests.get(ROOT_PAGE, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    return [
        link['href'] for link in soup.find_all('a', href=True)
        if 'laereplaner-lk20' in link['href'] and link['href'].endswith('.pdf')
    ]
```


### 2.3 PDF Downloader with Error Handling

```python
def download_pdf(url: str, max_retries: int = 3):
    """Robust PDF downloader with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            
            filename = url.split('/')[-1].split('?')[0]
            with open(f"data/raw_pdfs/{filename}", 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            log_error(f"Attempt {attempt+1} failed for {url}: {str(e)}")
            time.sleep(2 ** attempt)  # Exponential backoff
    return False
```


## 3. Advanced Features

### 3.1 Metadata Extraction

```python
def extract_metadata(pdf_path: str):
    """Extracts document metadata using PyPDF2"""
    with open(pdf_path, 'rb') as f:
        reader = PdfReader(f)
        return {
            'title': reader.metadata.title,
            'author': reader.metadata.author,
            'subject': reader.metadata.subject,
            'creation_date': reader.metadata.creation_date
        }
```


### 3.2 Automated File Renaming

```python
def standardize_filenames():
    """Converts UDIR codes to human-readable names"""
    naming_map = {
        'MAT01-05': 'Mathematics_G1-10',
        'NOR01-05': 'Norwegian_G1-10',
        # Add all identified code-name mappings
    }
    
    for file in Path('data/raw_pdfs').glob('*.pdf'):
        code = file.stem.split('_')[0]
        new_name = naming_map.get(code, code) + '.pdf'
        file.rename(f"data/processed/{new_name}")
```


## 4. Execution Workflow

### 4.1 Main Control Flow

```python
if __name__ == "__main__":
    pdf_links = extract_pdf_links()
    
    print(f"Found {len(pdf_links)} curriculum documents")
    
    with tqdm(total=len(pdf_links)) as pbar:
        for url in pdf_links:
            if download_pdf(url):
                pbar.update(1)
            else:
                log_error(f"Permanent failure: {url}")
    
    standardize_filenames()
    print("Processing complete")
```


## 5. Compliance Measures

### 5.1 Rate Limiting

```python
REQUEST_DELAY = 1.5  # Seconds between requests

def throttled_request(url):
    time.sleep(REQUEST_DELAY)
    return requests.get(url)
```


### 5.2 Robots.txt Compliance

```python
def check_robots_txt():
    robots = requests.get("https://www.udir.no/robots.txt").text
    if "Disallow: /lk20/" in robots:
        raise Exception("Scraping prohibited by robots.txt")
```


## 6. Validation \& Testing

### 6.1 Integrity Verification

```python
def verify_downloads():
    expected = set(pdf_links)
    downloaded = set(f.name for f in Path('data/raw_pdfs').glob('*.pdf'))
    
    missing = expected - downloaded
    if missing:
        print(f"Missing files: {len(missing)}")
```


### 6.2 Sample Validation Table

| Subject Code | Expected Pages | Actual Pages | Status |
| :-- | :-- | :-- | :-- |
| MAT01-05 | 42 | 42 | ✓ Valid |
| SAF01-04 | 38 | 38 | ✓ Valid |
| KRO01-05 | 29 | 29 | ✓ Valid |

## 7. Operational Considerations

### 7.1 Error Handling Strategies

```python
ERROR_HANDLERS = {
    403: lambda: rotate_user_agent(),
    404: lambda: log_error("Permanent missing resource"),
    429: lambda: time.sleep(60),
    500: lambda: retry_after(300)
}
```


### 7.2 Logging Configuration

```python
def setup_logging():
    logging.basicConfig(
        filename='logs/scrape_errors.log',
        level=logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
```


## 8. Complete Execution Script

```python
# scraper.py
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from tqdm import tqdm
import time
import logging

# Configuration
BASE_URL = "https://data.udir.no/kl06/v201906/laereplaner-lk20/"
REQUEST_DELAY = 1.5
MAX_RETRIES = 3

def main():
    setup_logging()
    check_robots_txt()
    
    try:
        pdf_links = extract_pdf_links()
        print(f"Identified {len(pdf_links)} curriculum documents")
        
        with tqdm(total=len(pdf_links)) as progress:
            for url in pdf_links:
                success = False
                for attempt in range(MAX_RETRIES):
                    try:
                        download_pdf(url)
                        success = True
                        break
                    except Exception as e:
                        logging.warning(f"Attempt {attempt+1} failed: {url} - {e}")
                        time.sleep(2 ** attempt)
                progress.update(1)
                time.sleep(REQUEST_DELAY)
        
        standardize_filenames()
        verify_downloads()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        
if __name__ == "__main__":
    main()
```


## 9. Post-Processing

### 9.1 Batch Conversion to Text

```bash
# Requires pdftotext (part of poppler-utils)
sudo apt-get install poppler-utils

find data/processed -name "*.pdf" -exec pdftotext {} \;
```


### 9.2 Checksum Verification

```python
def generate_checksums():
    hashes = {}
    for file in Path('data/processed').glob('*.pdf'):
        with open(file, 'rb') as f:
            hashes[file.name] = hashlib.md5(f.read()).hexdigest()
    return hashes
```

This implementation provides:

- Full audit trail through detailed logging
- Automatic retry mechanisms
- Compliance with ethical scraping practices
- Structured data organization
- Validation checks for data integrity

To execute:

```bash
python src/scraper.py
```

The complete code repository with configuration files is available at:
`https://github.com/example/lk20-scraper` (Note: This is a placeholder URL)

