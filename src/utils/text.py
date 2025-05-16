import re
import json
import requests
from io import BytesIO
from typing import Optional, Any, Dict
from models import CitedResponse

def has_date_in_content(content: str) -> bool:
    """
    Check if the content contains a date or year.
    Matches formats like:
    - 15 Feb 2025
    - Feb 2025
    - 2025
    """
    date_pattern = r'(?:\d{4}|(?:\d{1,2}\s)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s?\d{4})'
    return bool(re.search(date_pattern, content, re.IGNORECASE))

def parse_json_safely(content: str) -> Optional[Any]:
    """
    Safely parse JSON content from a string, handling cases where JSON might be
    embedded within other text.
    
    Args:
        content: String that may contain JSON
        
    Returns:
        Parsed JSON object if successful, None otherwise
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx + 1]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
    return None

def serialize_hit(hit: Any) -> Dict[str, Any]:
    """
    Serialize a Hit object to a dictionary.
    
    Args:
        hit: The hit object from vector search - can be either an object or dictionary
        
    Returns:
        Dict[str, Any]: Serialized hit as a dictionary
    """
    if isinstance(hit, dict):
        return hit
    
    return {
        "_id": getattr(hit, "_id", getattr(hit, "id", None)),
        "_score": getattr(hit, "_score", getattr(hit, "score", None)),
        "fields": getattr(hit, "fields", getattr(hit, "metadata", {}))
    }

def serialize_tool_result(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a tool result containing hits to a dictionary.
    
    Args:
        tool_result: The result from a tool call
        
    Returns:
        Dict[str, Any]: Serialized tool result
    """
    if isinstance(tool_result.get("results", []), list):
        results = tool_result.get("results", [])
        serializable_results = [
            hit if isinstance(hit, dict) else serialize_hit(hit) 
            for hit in results
        ]
        return {"query": tool_result.get("query"), "results": serializable_results}
    
    return tool_result

def format_structured_response(text: str, citation_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format a structured response with or without citation information.
    
    Args:
        text: The text content of the response
        citation_info: Optional citation information including file_url, citation text, and context
        
    Returns:
        Dict[str, Any]: Structured response as a dictionary
    """
    if citation_info:
        return CitedResponse(
            text=text,
            is_referenced=bool(citation_info.get("citation")),
            href=citation_info.get("file_url"),
            citations={"in-text": citation_info.get("citation")} if citation_info.get("citation") else None,
            context=citation_info.get("context")
        ).model_dump()
    else:
        return {"text": text, "is_referenced": False, "href": None}

# def get_pdf_page_count(pdf_url: str) -> int:
    """
    Get the number of pages in a PDF from a URL.
    
    Args:
        pdf_url: URL of the PDF file
        
    Returns:
        int: Number of pages in the PDF
        
    Raises:
        requests.RequestException: If there's an error downloading the PDF
        PyPDF2.PdfReadError: If there's an error reading the PDF
        ValueError: If the URL doesn't point to a valid PDF
    """
    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()
        
        if 'application/pdf' not in response.headers.get('content-type', '').lower():
            raise ValueError("URL does not point to a PDF file")
            
        pdf_file = BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        return len(pdf_reader.pages)
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error downloading PDF: {str(e)}")
    except PyPDF2.PdfReadError as e:
        raise PyPDF2.PdfReadError(f"Error reading PDF: {str(e)}")
    finally:
        if 'pdf_file' in locals():
            pdf_file.close()