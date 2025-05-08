from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import APIResponse
from http import HTTPStatus
import logging
from graph import query_graph
from models import GraphQueryRequest
import json

router = APIRouter()

@router.post("/generate", response_model=APIResponse)
async def generate_route(request: GraphQueryRequest):
    """
    Generate a response using the RAG graph
    
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

        try:
            result = await query_graph(request.query)
            
        except Exception as e:
            logging.error(f"Error in graph query flow: {str(e)}")
            response = APIResponse(
                success=False,
                error="Failed to execute graph query flow"
            )
            return JSONResponse(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                content=response.model_dump()
            )

        if not result:
            response = APIResponse(
                success=False,
                error="No response generated from the graph"
            )
            return JSONResponse(
                status_code=HTTPStatus.NOT_FOUND,
                content=response.model_dump()
            )

        response = APIResponse(
            success=True,
            data={"response": json.loads(result)}
        )
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content=response.model_dump()
        )

    except Exception as e:
        logging.error(f"Error in query_graph_route: {str(e)}")
        response = APIResponse(
            success=False,
            error="An internal server error occurred"
        )
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=response.model_dump()
        )
