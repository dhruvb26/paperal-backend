from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from utils.tavily_search import query_tavily

class WebSearchToolInput(BaseModel):
    """Input schema for WebSearchTool."""
    query: str = Field(..., description="The query to search the web for.")

class WebSearchTool(BaseTool):
    name: str = "Web Search Tool"
    description: str = (
        "Use this tool to search the web for a given query."
    )
    args_schema: Type[BaseModel] = WebSearchToolInput

    def _run(self, query: str) -> list[dict]:
        return query_tavily(query)
