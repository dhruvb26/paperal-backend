from typing import List
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start
from helpers import query_sonar, query_tavily, query_scholar, PineconeManager, SupabaseManager, extract_metadata
from utils import process_urls
import asyncio

class PaperSearchState(BaseModel):
    topic: str = ""
    urls: List[str] = []
    processed_data: List[dict] = []

class FindPapersFlow(Flow[PaperSearchState]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pinecone_manager = PineconeManager()
        self.supabase_manager = SupabaseManager()

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

        return combined_results
    
    @start()
    async def process_urls(self):
        processed_data = await process_urls(self.state.urls)
        self.state.processed_data = processed_data
        return processed_data

    @listen(process_urls)
    async def store_data(self):
        for data in self.state.processed_data:
            if not data:
                continue

            self.pinecone_manager.upsert_records(
                namespace="library", 
                data=data["vector_data"]
            )

            metadata = await extract_metadata(data["info"])
            
            record = {
                "title": data["title"],
                "description": metadata["description"],
                "metadata": {
                    "file_url": data["url"],
                    "year": metadata["year"],
                    "authors": metadata["authors"],
                    "citations": metadata["citations"]
                }
            }

            self.supabase_manager.add_to_library([record])

        return {"status": "success", "processed_count": len(self.state.processed_data)}

if __name__ == "__main__":
    flow = FindPapersFlow()
    asyncio.run(flow.kickoff_async(inputs={"topic": "AI", "urls": ["https://kj48tgjk7j.ufs.sh/f/5MeKTsJiYbqPJxl9Me6HybYKJ2Wd1ZrtGC3qaAX64gwViFmL", "https://kj48tgjk7j.ufs.sh/f/5MeKTsJiYbqP6kISfw8lPDnQNjVazA6RCBXqE5s8Kp4kOZ7t"]}))