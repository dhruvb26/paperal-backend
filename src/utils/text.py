import re
import json
import regex  
import requests
import unicodedata
from io import BytesIO
from unidecode import unidecode
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
    
def clean_split_text(text: str, preserve_unicode: bool = False) -> str:
    """
    Clean and split text by removing special characters and normalizing whitespace.

    Args:
        text: The text to clean and split
        
    Returns:
        str: Cleaned and split text
    """
    if not text:
        return ""
        
    text = unicodedata.normalize('NFKC', text)
    
    char_mappings = {
        # Quotes
        '"': '"',  # U+201C LEFT DOUBLE QUOTATION MARK
        '"': '"',  # U+201D RIGHT DOUBLE QUOTATION MARK
        ''': "'",  # U+2018 LEFT SINGLE QUOTATION MARK
        ''': "'",  # U+2019 RIGHT SINGLE QUOTATION MARK
        '‚': ',',  # U+201A SINGLE LOW-9 QUOTATION MARK
        '„': '"',  # U+201E DOUBLE LOW-9 QUOTATION MARK
        
        # Dashes and Hyphens
        '—': '-',  # U+2014 EM DASH
        '–': '-',  # U+2013 EN DASH
        '‐': '-',  # U+2010 HYPHEN
        '‑': '-',  # U+2011 NON-BREAKING HYPHEN
        '−': '-',  # U+2212 MINUS SIGN
        
        # Spaces and Breaks
        '\u00A0': ' ',  # NO-BREAK SPACE
        '\u2000': ' ',  # EN QUAD
        '\u2001': ' ',  # EM QUAD
        '\u2002': ' ',  # EN SPACE
        '\u2003': ' ',  # EM SPACE
        '\u2004': ' ',  # THREE-PER-EM SPACE
        '\u2005': ' ',  # FOUR-PER-EM SPACE
        '\u2006': ' ',  # SIX-PER-EM SPACE
        '\u2007': ' ',  # FIGURE SPACE
        '\u2008': ' ',  # PUNCTUATION SPACE
        '\u2009': ' ',  # THIN SPACE
        '\u200A': ' ',  # HAIR SPACE
        '\u200B': '',   # ZERO WIDTH SPACE
        '\u200C': '',   # ZERO WIDTH NON-JOINER
        '\u200D': '',   # ZERO WIDTH JOINER
        '\u2028': ' ',  # LINE SEPARATOR
        '\u2029': ' ',  # PARAGRAPH SEPARATOR
        
        # Other Special Characters
        '…': '...',  # U+2026 HORIZONTAL ELLIPSIS
        '•': '*',    # U+2022 BULLET
        '·': '*',    # U+00B7 MIDDLE DOT
        '‹': '<',    # U+2039 SINGLE LEFT-POINTING ANGLE QUOTATION MARK
        '›': '>',    # U+203A SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
        '«': '<<',   # U+00AB LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        '»': '>>',   # U+00BB RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
        '™': '(TM)', # U+2122 TRADE MARK SIGN
        '®': '(R)',  # U+00AE REGISTERED SIGN
        '©': '(C)',  # U+00A9 COPYRIGHT SIGN
    }
    
    for old, new in char_mappings.items():
        text = text.replace(old, new)
    
    if not preserve_unicode:
        text = unidecode(text)
    
    text = regex.sub(r'\r\n|\r|\n', ' ', text)
    text = regex.sub(r'\s+', ' ', text)
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in ('\n', '\t'))
    
    if not preserve_unicode:
        text = regex.sub(r'[\p{S}]', '', text)
    
    return text.strip()

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