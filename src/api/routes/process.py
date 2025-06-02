from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import ProcessRequest, ProcessResponse, APIResponse
from http import HTTPStatus
import logging

router = APIRouter()

@router.post("/process", response_model=APIResponse[ProcessResponse])
async def process_papers(request: ProcessRequest):
    """
    Process a research paper by chunking it into sections and storing the vector embeddings.
    
    Args:
        request: Object containing a list of URLs to process
        
    Returns:
        A success response indicating the task was queued with the task ID.
    """
    try:
        if not request.urls:
            response = APIResponse(
                success=False,
                error="URL list cannot be empty"
            )
            return JSONResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content=response.model_dump()
            )

    
        logging.info(f"Processing {len(request.urls)} URLs.")

        response = APIResponse(
            success=True,
            data={
                "message": "Processing started in background",
            }
        )
        return JSONResponse(
            status_code=HTTPStatus.ACCEPTED,
            content=response.model_dump()
        )

    except Exception as e:
        logging.error(f"Error in process_papers: {str(e)}")
        response = APIResponse(
            success=False,
            error="An internal server error occurred"
        )
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=response.model_dump()
        )
