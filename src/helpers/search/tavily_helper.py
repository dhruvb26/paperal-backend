from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

# try and keep query < 400 characters
def query_tavily(query: str | list[str], max_results: int = 5) -> list[dict]:
    """
    Search the web for a given query using Tavily.
    """
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    response = tavily_client.search(query, search_depth="advanced", chunks_per_source=3, max_results=max_results, include_domains=["arxiv.org"])

    all_results = []

    for result in response["results"]:
        # remove the raw_content from the result
        result.pop("raw_content")
        all_results.append(result["url"])


    return all_results
