import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_pdf_text(pdf_url: str):
    """
    Get the text from a PDF URL using Mistral.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"
    }
    
    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": pdf_url
        }
    }
    
    response = requests.post(
        "https://api.mistral.ai/v1/ocr",
        headers=headers,
        json=payload
    )
    
    if response.status_code != 200:
        raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
    
    data = response.json()
    result = ""
    for page in data["pages"]:
        result += page["markdown"]
    
    return result.strip()


def get_image_text(image_url: str):
    """
    Get the text from an image URL using Mistral.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"
    }
    
    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "image_url",
            "image_url": image_url
        }
    }
    
    response = requests.post(
        "https://api.mistral.ai/v1/ocr",
        headers=headers,
        json=payload
    )
    
    if response.status_code != 200:
        raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
    
    data = response.json()
    result = ""
    for page in data["pages"]:
        result += page["markdown"]
    
    return result.strip()
