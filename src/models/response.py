from typing_extensions import TypedDict
from typing import List, Optional, TypeVar, Generic
from pydantic import BaseModel

class Citations(TypedDict):
    in_text: str

class TopicMetadata(TypedDict):
    main_topic: str
    sub_topics: list[str]
    research_question: str

class DocumentMetadata(TypedDict):
    title: str
    description: str
    year: str
    authors: list[str]
    citations: Citations

class SearchResponse(TypedDict):
    urls: List[str]

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    MODEL_ERROR = "MODEL_ERROR"