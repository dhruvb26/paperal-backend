from typing import List
from pydantic import BaseModel, Field
import asyncio
from crewai.flow.flow import Flow, listen, start
from utils.sonar_search import query_sonar
from utils.tavily_search import query_tavily
from utils.scholar_search import query_scholar
from utils.chunking import process_urls

class PaperSearchState(BaseModel):
    topic: str = ""
    urls: List[str] = []

class FindPapersFlow(Flow[PaperSearchState]):
    @start()
    def initialize_search(self):

        return {"topic": self.state.topic}

    @listen(initialize_search)
    async def search_papers(self):
        sonar_query = f"""
        Find academic papers about {self.state.topic}. 
        
        Format the response as a structured list of papers.
        """
        
        tavily_query = f"academic research papers on {self.state.topic} filetype:pdf"

        scholar_query = f"{self.state.topic}"
        
        sonar_results = query_sonar(sonar_query)
        tavily_results = query_tavily(tavily_query)
        scholar_results = query_scholar(scholar_query)

        combined_results = sonar_results["urls"] + tavily_results + scholar_results

        self.state.urls = combined_results

        return {"urls": combined_results}
    
    @listen(search_papers)
    async def process_urls(self):

        await process_urls(self.state.urls)


async def run_flow():
    flow = FindPapersFlow()
    result = await flow.kickoff_async(inputs={"topic": "membership inference in language models"})
    return result

if __name__ == "__main__":
    asyncio.run(run_flow())