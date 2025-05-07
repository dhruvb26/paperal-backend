from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import QueryRequest, TopicMetadata, APIResponse
from helpers import extract_research_topic
from http import HTTPStatus
import logging

router = APIRouter()

@router.post("/extract-topic", response_model=APIResponse[TopicMetadata])
async def extract_topic(request: QueryRequest):
    """
    Extract research topic information from a user query

    Args:
        Object containing a key-value pair of "query"

    Returns: 
        A success boolean, data field if successful, and an error message if not.
    """
    try:
        if not request.query.strip():
            response = APIResponse(
                success=False,
                error="Query cannot be empty"
            )
            return JSONResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content=response.model_dump()
            )

        topic_data = await extract_research_topic(request.query)
        
        if not topic_data or not all(topic_data.get(key) for key in ["main_topic", "sub_topics", "research_question"]):
            response = APIResponse(
                success=False,
                error="Failed to extract valid topic information from the query"
            )
            return JSONResponse(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                content=response.model_dump()
            )

        response = APIResponse(
            success=True,
            data=topic_data
        )
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content=response.model_dump()
        )

    except ValueError as e:
        logging.error(f"Validation error in extract_topic: {str(e)}")
        response = APIResponse(
            success=False,
            error=str(e)
        )
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=response.model_dump()
        )
    except Exception as e:
        logging.error(f"Error in extract_topic: {str(e)}")
        response = APIResponse(
            success=False,
            error="An internal server error occurred"
        )
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=response.model_dump()
        ) 