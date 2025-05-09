from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import SearchRequest, SearchResponse, APIResponse
from helpers import query_sonar, query_tavily, query_scholar
from http import HTTPStatus
import logging

router = APIRouter()

@router.post("/search", response_model=APIResponse[SearchResponse])
async def search_papers(request: SearchRequest):
    """
    Search for papers based on a research topic
    
    Args:
        Object containing a key-value pair of "topic"

    Returns: 
        A success boolean, data field if successful, and an error message if not.
    """
    try:
        if not request.topic.strip():
            response = APIResponse(
                success=False,
                error="Topic cannot be empty"
            )
            return JSONResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content=response.model_dump()
            )

        try:
            
            sonar_query = f"""
                Find academic papers about {request.topic}. 
                
                Format the response as a structured list of papers.
                """
                
            tavily_query = f"academic research papers on {request.topic} filetype:pdf"

            scholar_query = f"{request.topic}"
            
            sonar_results = query_sonar(sonar_query)
            tavily_results = query_tavily(tavily_query)
            scholar_results = query_scholar(scholar_query)

            result = sonar_results["urls"] + tavily_results + scholar_results

        except Exception as e:
            logging.error(f"Error in paper search flow: {str(e)}")
            response = APIResponse(
                success=False,
                error="Failed to execute paper search flow"
            )
            return JSONResponse(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                content=response.model_dump()
            )

        if not result:
            response = APIResponse(
                success=False,
                error="No papers found for the given topic"
            )
            return JSONResponse(
                status_code=HTTPStatus.NOT_FOUND,
                content=response.model_dump()
            )

        response = APIResponse(
            success=True,
            data={"urls": result}
        )
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content=response.model_dump()
        )

    except Exception as e:
        logging.error(f"Error in search_papers: {str(e)}")
        response = APIResponse(
            success=False,
            error="An internal server error occurred"
        )
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=response.model_dump()
        )