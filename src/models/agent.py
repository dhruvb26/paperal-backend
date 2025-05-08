from pydantic import BaseModel, Field
from typing import Optional, TypedDict

class CitedResponse(BaseModel):
    """Model for structured output with citation information."""
    text: str = Field(description="The actual generated sentence")
    is_referenced: bool = Field(description="True if cited, otherwise False")
    href: Optional[str] = Field(description="File URL field of the chunk or null if not cited")
    citations: Optional[dict] = Field(description="Citation information if cited")
    context: Optional[str] = Field(description="Text from the vector chunk if cited")

class PaperState(TypedDict):
    paper_content: str

class GradeDocuments(BaseModel):
    """Grade documents using a binary score for relevance check."""

    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )