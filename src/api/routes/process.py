from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import ProcessRequest, ProcessResponse, APIResponse
from http import HTTPStatus
import logging
from api.hatchet_task import process_urls_task, UrlInput

router = APIRouter()

@router.post("/process", response_model=APIResponse[ProcessResponse])
async def process_papers(request: ProcessRequest):
    """
    Process a research paper by chunking it into sections and storing the vector embeddings.
    This is a background task handled by Hatchet that returns immediately after queueing the processing.
    
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

        process_urls_task.run_no_wait(input=UrlInput(urls=request.urls))
        logging.info(f"Processing {len(request.urls)} URLs in Hatchet.")

        response = APIResponse(
            success=True,
            data={
                "message": "Processing started in background",
                "task_id": "hatchet_task_id"
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
