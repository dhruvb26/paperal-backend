from fastapi import APIRouter
from fastapi.responses import JSONResponse
from helpers.ocr_helper import process_paper_citations, extract_citations_with_context
from models.request import OCRRequest

router = APIRouter()

@router.post("/ocr/citations")
async def ocr(request: OCRRequest):
    """
    Run Mistral OCR on a PDF to extract citations with context.

    Args: 
        request: Object with the URL of the PDF to process

    Returns:
        JSONResponse: Object with the citations with context
    """
    try:
        if not request.url:
            return JSONResponse(content={"error": "URL is required"}, status_code=400)
        
        result = process_paper_citations(request.url)

        print(result)

        return JSONResponse(content={"result": result}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
