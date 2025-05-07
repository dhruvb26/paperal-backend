from typing import Dict, Any, Optional
from pydantic import BaseModel, HttpUrl

class LibraryRecord(BaseModel):
    """
    Represents a single record in the library table.
    """
    title: str
    description: str
    metadata: Dict[str, Any]
    user_id: Optional[str] = None
    is_public: bool = False 