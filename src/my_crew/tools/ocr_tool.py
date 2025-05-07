from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from utils.ocr import get_pdf_text

class OCRToolInput(BaseModel):
    """Input schema for OCRTool."""
    pdf_url: str = Field(..., description="The url of the pdf file.")

class OCRTool(BaseTool):
    name: str = "OCR Tool"
    description: str = (
        "Use this tool to extract text from a given pdf url."
    )
    args_schema: Type[BaseModel] = OCRToolInput

    def _run(self, pdf_url: str) -> str:
        return get_pdf_text(pdf_url)
