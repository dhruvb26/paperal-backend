import re
from typing import Optional
from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException

def process_url(url: str) -> Optional[str]:
    """
    Process URLs from different sources and modify them based on specific patterns.
    Also verifies if the URL points to an actual PDF file.
    
    Args:
        url: The input URL to process
        
    Returns:
        Modified URL string or None if the URL doesn't match any patterns or isn't a valid PDF
    """
    url = url.strip()
    
    patterns = {
        'arxiv': r'https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/(\d+\.\d+)',
        'pmc': r'https?://(?:www\.)?ncbi\.nlm\.nih\.gov/pmc/articles/PMC(\d+)/?',
        'doi': r'https?://(?:dx\.)?doi\.org/(10\.\d+/[-._;()/:\w]+)',
    }
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
    except Exception:
        return None

    processed_url = None
    
    if re.match(patterns['arxiv'], url):
        processed_url = url.replace('/abs/', '/pdf/') + '.pdf'
    
    elif re.match(patterns['pmc'], url):
        processed_url = url + '/pdf'

    elif re.match(patterns['doi'], url):
        doi_match = re.match(patterns['doi'], url)
        if doi_match:
            processed_url = f'https://doi.org/{doi_match.group(1)}'
    
    else:
        processed_url = url if url.startswith(('http://', 'https://')) else None

    # Verify if the processed URL points to a PDF
    if processed_url:
        try:
            # Send a HEAD request first to check content type without downloading the full file
            headers = {'User-Agent': 'Mozilla/5.0'}  # Some servers require a user agent
            response = requests.head(processed_url, allow_redirects=True, headers=headers, timeout=10)
            
            # Some servers don't support HEAD requests, fall back to GET with stream
            if response.status_code == 405:  # Method not allowed
                response = requests.get(processed_url, stream=True, headers=headers, timeout=10)
            
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Check if content type indicates a PDF
            if 'application/pdf' in content_type:
                return processed_url
            return None
            
        except RequestException:
            return None

    return None

