import re
import json
from typing import Optional, Any

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