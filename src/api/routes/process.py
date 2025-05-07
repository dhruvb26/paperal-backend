from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import ProcessRequest, ProcessResponse, APIResponse
from http import HTTPStatus
import logging
from celery.result import AsyncResult
from api.tasks.process_urls_task import process_urls_task

router = APIRouter()

@router.post("/process-urls", response_model=APIResponse[ProcessResponse])
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

        task = process_urls_task.delay(request.urls)
        
        logging.info(f"Processing {len(request.urls)} URLs in Celery task {task.id}")

        response = APIResponse(
            success=True,
            data={
                "message": "Processing started in background",
                "task_id": task.id
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

@router.get("/task/{task_id}", response_model=APIResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a background processing task
    
    Args:
        task_id: The ID of the task to check
        
    Returns:
        The current status and result of the task if available
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
            
        response = APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": task_result.status,
                "result": task_result.result if task_result.ready() else None
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