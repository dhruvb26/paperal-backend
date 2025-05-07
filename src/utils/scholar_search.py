import requests
from bs4 import BeautifulSoup
from typing import List
import time
from urllib.parse import quote_plus

def query_scholar(query: str | List[str], max_results: int = 10) -> List[str]:
    """
    Search Google Scholar for a given query and return a list of URLs.
    
    Args:
        query: String or list of strings to search for
        max_results: Maximum number of results to return (default 10)
    
    Returns:
        List of URLs from the search results
    """
    if isinstance(query, list):
        query = " ".join(query)
    
    encoded_query = quote_plus(query)
    
    num_pages = (max_results + 9) // 10
    
    all_urls = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for page in range(num_pages):
        url = f"https://scholar.google.com/scholar?start={page*10}&q={encoded_query}&hl=en&as_sdt=0,5"
        
        try:
            time.sleep(2)
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.find_all("div", class_="gs_ri")
            
            for result in results:
                link_elem = result.find("a")
                if link_elem and "href" in link_elem.attrs:
                    all_urls.append(link_elem["href"])
                    
                if len(all_urls) >= max_results:
                    return all_urls[:max_results]
                    
        except requests.RequestException as e:
            print(f"Error fetching results from Google Scholar: {e}")
            break
            
    return all_urls
