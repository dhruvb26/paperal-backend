from fastapi import APIRouter
from fastapi.responses import JSONResponse
from models import APIResponse
from http import HTTPStatus
import logging
from models.request import AdaptRequest
from utils.dspy_test import adapt_to_style

router = APIRouter()

@router.post("/adapt", response_model=APIResponse)
async def adapt_route(request: AdaptRequest):
    """
    Adapt a piece of text to match a user's writing style
    """
    try:
        # Call the adapt_to_style function from utils.dspy_test
        result = adapt_to_style(request.writing_samples, request.text_to_adapt)
        
        # Return the result in the APIResponse format
        return APIResponse(success=True, data=result)
    except Exception as e:
        logging.error(f"Error adapting text: {e}")
        return APIResponse(success=False, error=str(e))