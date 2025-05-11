import re
from typing import Optional
from urllib.parse import urlparse

def process_url(url: str) -> Optional[str]:
    """
    Process URLs from different sources and modify them based on specific patterns.
    
    Args:
        url: The input URL to process
        
    Returns:
        Modified URL string or None if the URL doesn't match any patterns
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

    if re.match(patterns['arxiv'], url):
        return url.replace('/abs/', '/pdf/') + '.pdf'
    
    elif re.match(patterns['pmc'], url):
        return url + '/pdf'

    elif re.match(patterns['doi'], url):
        doi_match = re.match(patterns['doi'], url)
        if doi_match:
            return f'https://doi.org/{doi_match.group(1)}'
            
    return url if url.startswith(('http://', 'https://')) else None

