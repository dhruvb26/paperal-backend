from typing import Optional, Dict, Any
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from helpers import PineconeManager

class VectorSearchInput(BaseModel):
    query: str = Field(description="The search query to find relevant papers")

class VectorSearchTool(BaseTool):
    name: str = "vector_search"
    description: str = "Useful for searching through research papers to find relevant citations and content"
    args_schema: Optional[type[BaseModel]] = VectorSearchInput
    return_direct: bool = False

    def _run(
        self, 
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool to search through papers."""
        pinecone_manager = PineconeManager()
        response = pinecone_manager.query(namespace="library", query=query)

        result = {
            "query": query,
            "results": response
        }

        return result

    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously."""
        return self._run(query, run_manager=run_manager.get_sync() if run_manager else None)