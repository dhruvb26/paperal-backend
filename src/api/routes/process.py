from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import ProcessRequest, ProcessResponse, APIResponse
from http import HTTPStatus
import logging
from celery.result import AsyncResult
from api.hatchet_task import process_urls_task, UrlInput

router = APIRouter()

@router.post("/process", response_model=APIResponse[ProcessResponse])
async def process_papers(request: ProcessRequest):
    """
    Process a research paper by chunking it into sections and storing the vector embeddings.
    This is a background task handled by Celery that returns immediately after queueing the processing.
    
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

@router.get("/status/{task_id}", response_model=APIResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a background processing task
    
    Args:
        task_id: The ID of the task to check
        
    Returns:
        The current status and result of the task if available, including:
        - Overall task status
        - Number of URLs processed
        - Detailed success/failure information for each URL
    """
    try:
        task_result = AsyncResult(task_id)
        
        if task_result.failed():
            response = APIResponse(
                success=False,
                error=str(task_result.result)
            )
            return JSONResponse(
                status_code=HTTPStatus.OK,
                content=response.model_dump()
            )
            
        result = task_result.result if task_result.ready() else None
        if result:
            success = result.get("status") == "success"
            error = result.get("error")
            
            response = APIResponse(
                success=success,
                error=error,
                data={
                    "task_id": task_id,
                    "status": task_result.status,
                    "processed_urls": result.get("processed_urls", 0),
                    "results": result.get("results", {
                        "total": 0,
                        "successful": [],
                        "failed": []
                    })
                }
            )
        else:
            response = APIResponse(
                success=True,
                data={
                    "task_id": task_id,
                    "status": task_result.status,
                    "result": None
                }
            )
            
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content=response.model_dump()
        )
        
    except Exception as e:
        logging.error(f"Error checking task status: {str(e)}")
        response = APIResponse(
            success=False,
            error="Error checking task status"
        )
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=response.model_dump()
        )