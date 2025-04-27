"""Utility helpers for podcast transcript scraping."""
from pathlib import Path
import json
import logging
import re
from typing import Dict, List, Optional

# --- Project directories ---------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT_DIR / "logs"

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# --- Logging ---------------------------------------------------------------
logging.basicConfig(
    filename=LOGS_DIR / "podcast_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- HTTP headers ----------------------------------------------------------
HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0 "
        "PodcastScraper/1.0 (+https://github.com/YOUR_REPO_HERE)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
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


def log_warning(message: str) -> None:
    """Log warning message to file and stderr."""
    logging.warning(message)
    print(f"WARNING: {message}")


# ---------------------------------------------------------------------------

def setup_directories(output_base_dir: Path) -> Dict[str, Path]:
    """Create and return paths for the podcast scraper output."""
    raw_html_dir = output_base_dir / "raw_html"
    transcripts_dir = output_base_dir / "transcripts"

    # Ensure they exist
    output_base_dir.mkdir(parents=True, exist_ok=True)
    raw_html_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    return {
        "output_dir": output_base_dir,
        "raw_html": raw_html_dir,
        "transcripts": transcripts_dir,
    }


def sanitize_filename(url_or_slug: str) -> str:
    """Convert a URL or slug to a filesystem-safe filename (without extension)."""
    # If it looks like a URL, process it
    if url_or_slug.startswith('http'):
        filename = re.sub(r'^https?://', '', url_or_slug)
        filename = filename.split('?')[0]  # strip query string
        filename = filename.rstrip('/')
        filename = filename.replace('/', '-')
    else: # Assume it's already a slug/filename part
        filename = url_or_slug
        
    filename = re.sub(r'[:\*?"<>|]+', '_', filename) # Slightly stricter regex
    # Replace multiple underscores/hyphens with one
    filename = re.sub(r'[-_]+', '_', filename)
    # Remove leading/trailing underscores
    filename = filename.strip('_')
    
    return filename[:100]  # Shorter truncation limit


# ------------------------- text chunking -----------------------------------

def _simple_tokenize(txt: str) -> List[str]:
    return re.findall(r"\w+|[^\w\s]", txt)


def chunk_text(text: str, title: Optional[str] = None, max_tokens: int = 512, overlap_tokens: int = 50) -> List[Dict]:
    """Split *text* into ~max_tokens chunks preserving paragraphs, with overlap.
    
    Args:
        text: The input text string.
        title: Optional title to prepend to chunks.
        max_tokens: Approximate maximum tokens per chunk.
        overlap_tokens: Number of tokens to overlap between consecutive chunks.
        
    Returns:
        List of dictionaries, each with 'text' and 'tokens' keys.
    """
    if overlap_tokens >= max_tokens:
        log_warning(f"Overlap tokens ({overlap_tokens}) >= max tokens ({max_tokens}). Setting overlap to 0.")
        overlap_tokens = 0
        
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    initial_chunks: List[Dict] = []

    cur_lines: List[str] = []
    cur_tokens = 0

    def _flush():
        nonlocal cur_lines, cur_tokens
        if cur_lines:
            body = " ".join(cur_lines)
            # Initial title prepending logic (can be refined based on overlap)
            # We might only want title on the very first chunk later
            if title and not body.lower().startswith(title.lower()):
                if len(body) > 20:
                     body = f"{title.strip()}: {body}"
            initial_chunks.append({"text": body, "tokens": cur_tokens})
            cur_lines = []
            cur_tokens = 0

    for para in paragraphs:
        tokens = len(_simple_tokenize(para))
        if tokens == 0:
            continue
            
        # If a single paragraph exceeds max_tokens, split it aggressively
        if tokens > max_tokens:
            # Flush any existing lines first
            _flush() 
            
            words = para.split()
            seg: List[str] = []
            seg_tokens = 0
            word_tokens = [_simple_tokenize(w) for w in words] # Pre-tokenize words
            
            for i, w in enumerate(words):
                w_token_count = len(word_tokens[i])
                if seg_tokens + w_token_count > max_tokens:
                    # Flush segment as a chunk
                    cur_lines = [" ".join(seg)]
                    cur_tokens = seg_tokens
                    _flush()
                    seg, seg_tokens = [], 0
                seg.append(w)
                seg_tokens += w_token_count
            # Flush any remaining part of the long paragraph
            if seg:
                cur_lines = [" ".join(seg)]
                cur_tokens = seg_tokens
                _flush()
            continue # Move to next paragraph
            
        # Regular paragraph handling
        if cur_tokens + tokens > max_tokens:
            _flush()
            
        cur_lines.append(para)
        cur_tokens += tokens
        
    _flush() # Flush any remaining lines

    if not initial_chunks: # Handle case of empty text
        return []

    # --- Add overlap --- #
    if overlap_tokens == 0 or len(initial_chunks) <= 1:
        return initial_chunks # No overlap needed/possible
        
    overlapped_chunks: List[Dict] = [initial_chunks[0]] # Start with the first chunk as is
    
    for i in range(1, len(initial_chunks)):
        prev_chunk_text = initial_chunks[i-1]['text']
        current_chunk = initial_chunks[i]
        
        prev_tokens = _simple_tokenize(prev_chunk_text)
        if len(prev_tokens) <= overlap_tokens:
            overlap_prefix = prev_chunk_text # Overlap with the whole previous chunk
        else:
            overlap_token_slice = prev_tokens[-overlap_tokens:]
            # Simple re-joining, might lose some original spacing nuance but ok for overlap
            overlap_prefix = " ".join(overlap_token_slice) 
            
        # Prepend overlap, recalculate text and tokens for the new chunk
        new_text = overlap_prefix + " " + current_chunk['text']
        new_tokens = len(_simple_tokenize(new_text))
        
        # Optionally remove title from subsequent chunks if it was added
        # This logic might need adjustment based on how titles are used downstream
        # if title and new_text.lower().startswith(title.lower() + ":"):
        #    pass # Keep title if desired on all chunks
            
        overlapped_chunks.append({"text": new_text, "tokens": new_tokens})

    return overlapped_chunks

# ---------------------------------------------------------------------------
