import requests
from dotenv import load_dotenv
import os

load_dotenv()

def query_sonar(query: str) -> list[str]:
    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "response_format": { "type": "json_schema", "json_schema": {"schema": {"type": "array", "items": {"type": "string"}}} },
        "return_related_questions": True,
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that helps with finding peer-review papers that are accesible as a pdf on a given topic. Only return the urls of the papers without any other text or markdown formatting."
            },
            {
                "role": "user",
                "content": query
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    response_json = response.json()

    result_object = {
        "urls": response_json.get('citations', []),
        "related_questions": response_json.get('related_questions', [])
    }
    
    return result_object