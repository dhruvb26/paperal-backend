import os
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()

def get_pdf_text(pdf_url: str):
    """
    Get the text from a PDF URL using Mistral AI.
    """
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

    pdf_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": pdf_url
        }
    )

    result = ""
    for page in pdf_response.pages:
        result += page.markdown

    return result.strip()


def get_image_text(image_url: str):
    """
    Get the text from an image URL using Mistral AI.
    """
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

    image_response = client.ocr.process(
        model="mistral-ocr-latest",
    document={
        "type": "image_url",
            "image_url": image_url
        }
    )

    result = ""
    for page in image_response.pages:
        result += page.markdown

    return result.strip()
