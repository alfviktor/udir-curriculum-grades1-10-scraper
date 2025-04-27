"""TakeoverPod transcript scraper.

Scrapes episode transcripts from TakeoverPod website.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from tqdm import tqdm
import xml.etree.ElementTree as ET

from src.utilities import (
    setup_directories,
    log_error,
    log_info,
    chunk_text,
    sanitize_filename,
    HEADERS
)

from datetime import datetime

# --- Constants ---
BASE_URL = "https://www.takeoverpod.com"
EPISODES_URL = urljoin(BASE_URL, "/episodes")
TITLE_SELECTOR = "h1.heading-style-h3"  # Selector for the main episode title
PUB_DATE_SELECTOR = ".episode-template-hero_date .text-size-caption.is-date" # Selector for publication date
TRANSCRIPT_SELECTOR = ".transcript_srollable .w-richtext"  # Selector for the transcript div
OUTPUT_DIR = Path("episodes")
REQUEST_DELAY = 1.0  # Increased delay for politeness
MAX_CONCURRENT_REQUESTS = 5 # Reduced concurrency

# --- Scraper Class ---
class PodcastScraper:
    """Scraper for TakeoverPod episode transcripts."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.base_url = BASE_URL
        self.episodes_url = EPISODES_URL
        
        # Setup directories 
        self.directories = setup_directories(OUTPUT_DIR)
        
        # URL sets
        self.episode_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        # Results store: (url, title, transcript, pub_date_str)
        self.results: List[Tuple[str, str, str, Optional[str]]] = [] 
        
    async def fetch_url(self, session: aiohttp.ClientSession, url: str) -> Tuple[str, bytes, str]:
        """Fetch content from URL."""
        try:
            async with session.get(url, headers=HEADERS) as response:
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '')
                content = await response.read()
                return url, content, content_type
        except Exception as e:
            log_error(f"Failed to fetch {url}: {e}")
            return url, b"", ""

    async def discover_urls(self) -> None:
        """Discover episode URLs from the main episodes page."""
        log_info(f"Discovering episode URLs from {self.episodes_url}...")
        discovered_count = 0
        try:
            # Use a temporary session to fetch the main page
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                url, content, content_type = await self.fetch_url(session, self.episodes_url)
                
                if not content or 'html' not in content_type.lower():
                    log_error(f"Failed to fetch or received non-HTML content from {self.episodes_url}")
                    return

            # Parse the main episodes page
            soup = BeautifulSoup(content, 'html.parser')
            
            # --- Find episode links (Adapt selector based on actual site structure) ---
            # Common patterns: look for links within article tags, list items, or divs with specific classes.
            # Example: Assuming links are in '<a>' tags within '<article class="episode-item">'
            # Adjust '.episode-item a' selector as needed!
            episode_links = soup.select('a[href*="/episodes/"]') # General selector for links containing /episodes/
            
            if not episode_links:
                 log_warning(f"No episode links found using selector 'a[href*="/episodes/"]'. Check selector.")
                 # Try a broader search if the specific one fails - might get non-episode links too
                 episode_links = soup.find_all('a', href=True)

            found_urls = set()
            for link in episode_links:
                href = link.get('href')
                if href and href.startswith('/episodes/') and len(href) > len('/episodes/'): # Basic check
                    # Construct absolute URL
                    full_url = urljoin(self.base_url, href)
                    # Avoid adding the main episodes page itself if it matches
                    if full_url != self.episodes_url:
                         found_urls.add(full_url)
                         discovered_count += 1
            
            self.episode_urls = found_urls
            if discovered_count > 0:
                 log_info(f"Discovered {discovered_count} potential episode URLs.")
            else:
                 log_warning(f"Could not discover any episode URLs matching the pattern '/episodes/...' from {self.episodes_url}")
                 log_info("Please verify the HTML structure of the page and update the link selector in discover_urls if necessary.")

        except Exception as e:
            log_error(f"Error during URL discovery: {e}")

    async def process_html(self, url: str, content: bytes) -> Tuple[str, str, str, Optional[str]] | None:
        """Process episode HTML, extract title, transcript, and publication date."""
        try:
            # Generate filename from URL slug
            slug = url.strip('/').split('/')[-1]
            filename = sanitize_filename(slug)
            
            # Save raw HTML
            raw_html_path = self.directories['raw_html'] / f"{filename}.html"
            with open(raw_html_path, 'wb') as f:
                f.write(content)

            # Parse with beautifulsoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract title
            title_tag = soup.select_one(TITLE_SELECTOR)
            if not title_tag:
                log_error(f"Title selector '{TITLE_SELECTOR}' not found for {url}")
                title = f"Unknown Title ({Path(urlparse(url).path).name})"
            else:
                title = title_tag.get_text(strip=True)
                
            # Extract publication date
            pub_date_str: Optional[str] = None
            date_element = soup.select_one(PUB_DATE_SELECTOR)
            if date_element:
                raw_date = date_element.get_text(strip=True)
                try:
                    # Example format: "December 8, 2021"
                    dt_object = datetime.strptime(raw_date, "%B %d, %Y")
                    pub_date_str = dt_object.strftime("%Y-%m-%d") # Standard ISO format
                    log_info(f"Extracted date: {pub_date_str} from '{raw_date}' for {url}")
                except ValueError as e:
                    log_warning(f"Could not parse date '{raw_date}' for {url}: {e}")
            else:
                log_warning(f"Publication date selector '{PUB_DATE_SELECTOR}' not found for {url}")

            # Extract transcript
            transcript_element = soup.select_one(TRANSCRIPT_SELECTOR)
            
            if not transcript_element:
                log_error(f"Transcript selector not found for {url}")
                return None

            # --- Placeholder: Cleaning Logic Needed --- #
            # Simple text extraction for now
            cleaned_text = transcript_element.get_text(separator='\n', strip=True) 
            
            # --- Transcript Cleaning --- # 
            # 1. Remove timestamps like [00:12:34] or [00:12:34.567]
            cleaned_text = re.sub(r'\[\d{2}:\d{2}:\d{2}(?:\.\d+)?\]', '', cleaned_text)
            # 2. Remove speaker labels (like "Speaker Name:") at the start of lines
            cleaned_text = re.sub(r'^[A-Za-z0-9 ]+:', '', cleaned_text, flags=re.MULTILINE)
            # 3. Replace multiple whitespace chars (including newlines) with a single space
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            # 4. Strip leading/trailing whitespace from the final string
            cleaned_text = cleaned_text.strip()

            log_info(f"Successfully processed: {title}")
            return url, title, cleaned_text, pub_date_str
            
        except Exception as e:
            log_error(f"Error processing HTML for {url}: {e}")
            return None

    async def scrape(self) -> None:
        """Run the full scraping process."""
        start_time = time.monotonic()
        log_info("Starting TakeoverPod transcript scrape...")
        
        await self.discover_urls()
        
        if not self.episode_urls:
            log_error("No episode URLs discovered. Exiting.")
            return
            
        log_info(f"Fetching and processing {len(self.episode_urls)} episodes...")
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        tasks = []
        
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            progress_bar = tqdm(total=len(self.episode_urls), desc="Scraping Episodes", unit="ep")
            
            async def process_with_semaphore(url):
                async with semaphore:
                    if url not in self.processed_urls:
                        try:
                            _, content, content_type = await self.fetch_url(session, url)
                            if content and 'html' in content_type.lower():
                                result = await self.process_html(url, content)
                                if result:
                                    self.results.append(result)
                                self.processed_urls.add(url)
                            elif content: 
                                log_error(f"Skipping non-HTML content at {url} ({content_type})")
                                self.processed_urls.add(url) # Mark as processed to avoid retries
                        except Exception as e:
                             log_error(f"Error in semaphore task for {url}: {e}")
                        finally:
                            progress_bar.update(1)
                            await asyncio.sleep(REQUEST_DELAY)
                    else:
                        progress_bar.update(1) # Update progress even if skipped
            
            tasks = [process_with_semaphore(url) for url in self.episode_urls]
            await asyncio.gather(*tasks)
            progress_bar.close()

        # --- Placeholder: Saving Logic Needed --- #
        # Call save_results method here after loop
        await self.save_results()

        elapsed_time = time.monotonic() - start_time
        log_info(f"Scraping finished in {elapsed_time:.2f} seconds.")
        log_info(f"Processed {len(self.processed_urls)} URLs.")
        log_info(f"Successfully extracted {len(self.results)} transcripts.")
        
    async def save_results(self):
        """Save cleaned transcripts and generate chunked JSONL file with metadata."""
        log_info(f"Saving {len(self.results)} transcripts and generating chunks...")
        
        jsonl_path = self.directories['output_dir'] / "chunks.jsonl"
        
        with open(jsonl_path, 'w', encoding='utf-8') as f_jsonl:
            for url, title, transcript, pub_date_str in tqdm(self.results, desc="Saving Results", unit="transcript"):
                
                # --- Save individual transcript --- #
                filename_base = sanitize_filename(title)
                transcript_path = self.directories['transcripts'] / f"{filename_base}.txt"
                with open(transcript_path, 'w', encoding='utf-8') as f_txt:
                    f_txt.write(transcript)
                    
                # --- Chunk and save to JSONL --- #
                chunks = chunk_text(transcript, title=title, max_tokens=500) # Pass title and use 500 token limit
                
                for i, chunk_dict in enumerate(chunks):
                    metadata = {
                        "episode_url": url,
                        "title": title,
                        "chunk_index": i,
                        "publication_date": pub_date_str, # Add the date
                        "total_chunks_in_doc": len(chunks)
                    }
                    
                    record = {
                        "text": chunk_dict['text'],
                        "metadata": metadata,
                        # Optionally add token count if needed downstream
                        # "tokens": chunk_dict['tokens'] 
                    }
                    f_jsonl.write(json.dumps(record, ensure_ascii=False) + '\n')

        log_info(f"Chunks saved to {jsonl_path}")

# --- Main execution block --- #
async def main():
    """Main entry point to run the scraper."""
    scraper = PodcastScraper()
    await scraper.scrape()

if __name__ == "__main__":
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    asyncio.run(main())
