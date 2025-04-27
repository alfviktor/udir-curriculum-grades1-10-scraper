"""Bank information scraper.

Scrapes public information from bank websites including HTML pages and PDFs.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from tqdm import tqdm
import xml.etree.ElementTree as ET

from src.utilities import (
    setup_bank_directories,
    log_error,
    log_info,
    chunk_text,
    sanitize_filename,
    HEADERS
)

from datetime import datetime

REQUEST_DELAY = 0.5  # seconds between requests
MAX_CONCURRENT_REQUESTS = 8  # limit concurrent requests

class BankScraper:
    """Scraper for bank websites."""
    
    def __init__(self, bank_name: str, domain: str):
        """Initialize with bank name and domain."""
        self.bank_name = bank_name
        self.domain = domain
        if not domain.startswith('http'):
            self.domain = f'https://{domain}'
        
        # Setup directories
        self.directories = setup_bank_directories(bank_name)
        
        # URL sets
        self.html_urls: Set[str] = set()
        self.pdf_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        
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

    def extract_urls_from_sitemap(self, sitemap_url: str) -> Set[str]:
        """Extract URLs from sitemap XML."""
        urls = set()
        try:
            response = requests.get(sitemap_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            # Handle sitemap index files
            root = ET.fromstring(response.content)
            
            # Look for nested sitemaps
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            sitemap_tags = root.findall('.//sm:sitemap/sm:loc', namespaces)
            
            if sitemap_tags:
                for sitemap_tag in sitemap_tags:
                    nested_sitemap_url = sitemap_tag.text
                    if nested_sitemap_url:
                        urls.update(self.extract_urls_from_sitemap(nested_sitemap_url))
            
            # Extract URLs
            url_tags = root.findall('.//sm:url/sm:loc', namespaces)
            for url_tag in url_tags:
                if url_tag.text:
                    urls.add(url_tag.text)
                    
            log_info(f"Found {len(urls)} URLs in sitemap {sitemap_url}")
            return urls
        except Exception as e:
            log_error(f"Error processing sitemap {sitemap_url}: {e}")
            return urls

    async def discover_urls(self) -> None:
        """Discover URLs by checking sitemaps and robots.txt."""
        sitemap_url = f"{self.domain}/sitemap.xml"
        robots_url = f"{self.domain}/robots.txt"
        
        # Try sitemap first
        try:
            self.html_urls.update(self.extract_urls_from_sitemap(sitemap_url))
        except Exception as e:
            log_error(f"Sitemap error: {e}")
        
        # If sitemap failed or found no URLs, try robots.txt
        if not self.html_urls:
            try:
                response = requests.get(robots_url, headers=HEADERS, timeout=15)
                if response.ok:
                    for line in response.text.split('\n'):
                        if line.lower().startswith('sitemap:'):
                            sitemap_url = line.split(':', 1)[1].strip()
                            self.html_urls.update(self.extract_urls_from_sitemap(sitemap_url))
            except Exception as e:
                log_error(f"Robots.txt error: {e}")
                
        # Filter URLs by domain and separate PDF URLs
        filtered_urls = set()
        for url in self.html_urls:
            parsed_url = urlparse(url)
            if parsed_url.netloc == urlparse(self.domain).netloc:
                if url.lower().endswith('.pdf'):
                    self.pdf_urls.add(url)
                else:
                    filtered_urls.add(url)
        
        self.html_urls = filtered_urls
        
        log_info(f"Discovered {len(self.html_urls)} HTML URLs and {len(self.pdf_urls)} PDF URLs")

    async def process_html(self, url: str, content: bytes) -> None:
        """Process HTML content, extract text and PDF links."""
        try:
            # Parse with beautifulsoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract title before cleaning
            title = soup.title.string if soup.title else url.split('/')[-1]
            
            # Create a copy for cleaned version
            clean_soup = BeautifulSoup(str(soup), 'html.parser')
            
            # Remove unwanted elements more aggressively from clean version
            for selector in [
                'nav', 'footer', 'header', '.cookie-banner', '.cookie-consent', 
                'script', 'style', '.navigation', '.menu', '.sidebar', '.widget',
                '.social', '.share', '.comments', '.ads', 'iframe', '#gdpr'
            ]:
                for element in clean_soup.select(selector):
                    element.decompose()
            
            # Extract text from main content with better prioritization
            main_selectors = [
                'main', 'article', '.content', '#content', '.main-content',
                '.entry-content', '.post-content', '.page-content'
            ]
            
            main_content = None
            for selector in main_selectors:
                main_content = clean_soup.select_one(selector)
                if main_content and main_content.get_text(strip=True):
                    break
            
            # Extract text, fallback to body if needed
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                # Try to identify and skip menus/headers
                body = clean_soup.body
                if body:
                    # Remove very short text blocks (likely menus/buttons)
                    for p in body.find_all(['p', 'div', 'span']):
                        if len(p.get_text(strip=True)) < 15:
                            p.decompose()
                    text = body.get_text(separator=' ', strip=True)
                else:
                    text = clean_soup.get_text(separator=' ', strip=True)
            
            # Save raw HTML
            filename = sanitize_filename(url)
            html_path = self.directories['raw_html'] / f"{filename}.html"
            with open(html_path, 'wb') as f:
                f.write(content)
                
            # Also save processed/cleaned HTML
            processed_dir = self.directories['bank_dir'] / "processed"
            processed_dir.mkdir(exist_ok=True)
            processed_html_path = processed_dir / f"{filename}.txt"
            with open(processed_html_path, 'w', encoding='utf-8') as f:
                f.write(f"TITLE: {title}\n\n")
                f.write(f"URL: {url}\n\n")
                f.write(f"CONTENT:\n{text}")
            
            # Write metadata JSON
            metadata = {
                "title": title,
                "source_url": url,
                "bank_name": self.bank_name,
                "doc_type": "webpage",
                "scope": "bank_info",
                "extraction_date": datetime.utcnow().isoformat()
            }
            meta_path = processed_dir / f"{filename}.metadata.json"
            with open(meta_path, 'w', encoding='utf-8') as mf:
                json.dump(metadata, mf, ensure_ascii=False, indent=2)
            
            # Process text into chunks
            chunks = chunk_text(text, title)
            
            # Append chunks to jsonl file
            with open(self.directories['chunks_file'], 'a', encoding='utf-8') as f:
                for chunk in chunks:
                    record = {
                        'bank': self.bank_name,
                        'url': url,
                        'title': title,
                        'chunk': chunk['text'],
                        'tokens': chunk['tokens']
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            # Find additional PDF links with more aggressive patterns
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Skip empty or javascript links
                if not href or href.startswith('javascript:') or href == '#':
                    continue
                
                full_url = urljoin(url, href)
                
                # Match PDFs by extension or content type hints in URL
                is_pdf = (
                    full_url.lower().endswith('.pdf') or 
                    '/pdf/' in full_url.lower() or
                    'application/pdf' in link.get('type', '') or
                    'pdf' in link.get('download', '')
                )
                
                # Check domain, but also allow common CDN domains that might host bank PDFs
                parsed_url = urlparse(full_url)
                main_domain = '.'.join(urlparse(self.domain).netloc.split('.')[-2:])
                parsed_domain = '.'.join(parsed_url.netloc.split('.')[-2:])
                
                domain_match = (
                    parsed_url.netloc == urlparse(self.domain).netloc or
                    (parsed_domain == main_domain) or
                    ('cdn' in parsed_url.netloc and main_domain in parsed_url.netloc)
                )
                
                if is_pdf and domain_match:
                    log_info(f"Found PDF: {full_url}")
                    self.pdf_urls.add(full_url)
                    
        except Exception as e:
            log_error(f"Error processing HTML from {url}: {e}")

    async def process_pdf(self, url: str, content: bytes) -> None:
        """Process PDF content, extract text."""
        try:
            # Save raw PDF
            filename = sanitize_filename(url)
            pdf_path = self.directories['raw_pdf'] / f"{filename}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(content)
                
            # Extract text from PDF
            try:
                text = extract_text(pdf_path)
            except Exception as e:
                log_error(f"Error extracting text from PDF {url}: {e}")
                text = f"[PDF EXTRACTION ERROR: {e}]"  # Fallback to avoid complete failure
            
            # Get better title from PDF filename or URL
            filename_parts = url.split('/')[-1].replace('.pdf', '').split('-')
            title = ' '.join(word.capitalize() for word in filename_parts)
            
            # Save processed PDF text
            processed_dir = self.directories['bank_dir'] / "processed"
            processed_dir.mkdir(exist_ok=True)
            processed_pdf_path = processed_dir / f"{sanitize_filename(url)}.txt"
            with open(processed_pdf_path, 'w', encoding='utf-8') as f:
                f.write(f"TITLE: {title}\n\n")
                f.write(f"URL: {url}\n\n")
                f.write(f"CONTENT:\n{text}")
            
            # Write metadata JSON for PDF
            metadata = {
                "title": title,
                "source_url": url,
                "bank_name": self.bank_name,
                "doc_type": "pdf",
                "scope": "bank_info",
                "extraction_date": datetime.utcnow().isoformat()
            }
            meta_path = processed_dir / f"{sanitize_filename(url)}.metadata.json"
            with open(meta_path, 'w', encoding='utf-8') as mf:
                json.dump(metadata, mf, ensure_ascii=False, indent=2)
            
            # Process text into chunks
            chunks = chunk_text(text, title)
            
            # Append chunks to jsonl file
            with open(self.directories['chunks_file'], 'a', encoding='utf-8') as f:
                for chunk in chunks:
                    record = {
                        'bank': self.bank_name,
                        'url': url,
                        'title': title,
                        'chunk': chunk['text'],
                        'tokens': chunk['tokens']
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    
        except Exception as e:
            log_error(f"Error processing PDF from {url}: {e}")
            
    async def process_urls(self) -> None:
        """Process all discovered URLs."""
        # Determine HTML and PDF URLs
        html_urls = list(self.html_urls)
        pdf_urls = list(self.pdf_urls)
        total_urls = len(html_urls) + len(pdf_urls)
        
        if total_urls == 0:
            log_error("No URLs to process")
            return
            
        log_info(f"Processing {total_urls} URLs ({len(html_urls)} HTML, {len(pdf_urls)} PDF)")
        
        # Create a semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def process_with_limit(url, is_pdf=False):
            async with semaphore:
                await asyncio.sleep(REQUEST_DELAY)
                async with aiohttp.ClientSession() as session:
                    # Handle URLs differently based on expected type
                    url, content, content_type = await self.fetch_url(session, url)
                    
                    if not content:
                        return
                    
                    # Route based on expected type and content
                    is_pdf_content = (
                        'application/pdf' in content_type or 
                        url.lower().endswith('.pdf') or
                        (content[:4] == b'%PDF')  # PDF magic bytes
                    )
                    
                    if is_pdf or is_pdf_content:
                        log_info(f"Processing PDF: {url}")
                        await self.process_pdf(url, content)
                    else:
                        await self.process_html(url, content)
                    self.processed_urls.add(url)

        # Process HTML URLs first to collect PDF links
        with tqdm(total=total_urls, desc=f"Scraping {self.bank_name}") as pbar:
            # HTML batch
            html_tasks = [asyncio.create_task(process_with_limit(u)) for u in html_urls]
            for i in range(0, len(html_tasks), 5):  # Process in smaller batches
                batch = html_tasks[i:i+10]
                await asyncio.gather(*batch)
                pbar.update(len(batch))
            # Get newly discovered PDFs that weren't in the original set
            current_pdf_urls = list(self.pdf_urls - set(pdf_urls))
            if current_pdf_urls:
                log_info(f"Found {len(current_pdf_urls)} new PDF URLs during HTML processing")
                pdf_urls.extend(current_pdf_urls)
            
            # Create PDF tasks with is_pdf flag set to True
            pdf_tasks = [asyncio.create_task(process_with_limit(u, is_pdf=True)) for u in pdf_urls]
            for i in range(0, len(pdf_tasks), 10):
                batch = pdf_tasks[i:i+10]
                await asyncio.gather(*batch)
                pbar.update(len(batch))
        
        log_info(f"Completed processing {len(self.processed_urls)} URLs for {self.bank_name}")
        
    async def scrape(self) -> None:
        """Run the complete scraping process."""
        await self.discover_urls()
        await self.process_urls()
        

async def scrape_bank(bank_name: str, domain: str) -> None:
    """Scrape a single bank."""
    scraper = BankScraper(bank_name, domain)
    await scraper.scrape()
    
async def scrape_banks(bank_config: Dict[str, str]) -> None:
    """Scrape multiple banks sequentially."""
    start_time = time.time()
    
    for bank_name, domain in bank_config.items():
        log_info(f"Starting scrape of {bank_name} ({domain})")
        await scrape_bank(bank_name, domain)
        
    duration = time.time() - start_time
    log_info(f"Completed all bank scrapes in {duration:.2f} seconds")

def main() -> None:
    """Main entry point."""
    # Load bank configuration
    try:
        with open(Path(__file__).parent.parent / 'config' / 'banks.json', 'r', encoding='utf-8') as f:
            bank_config = json.load(f)
            
        if not bank_config:
            log_error("No banks configured in config/banks.json")
            return
            
        # Run async scraper
        asyncio.run(scrape_banks(bank_config))
        
    except Exception as e:
        log_error(f"Unhandled error in main: {e}")

if __name__ == "__main__":
    main()
