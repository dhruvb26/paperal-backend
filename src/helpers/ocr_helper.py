import os
import requests
from dotenv import load_dotenv
import re
from mistralai import Mistral

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

def process_paper_citations(pdf_url: str):
    """
    Process a paper URL to extract citations and store them in Neo4j.
    
    Args:
        pdf_url (str): URL of the paper to process
        
    Returns:
        tuple: (title, citations) where title is the paper title and citations is a list of citation dictionaries
    """
    api_key = os.getenv("MISTRAL_API_KEY")
    client = Mistral(api_key=api_key)
    model = "mistral-small-latest"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """Extract the title and ALL citations from this academic paper. Format the response exactly as follows:

                                Title: [paper title]

                                Citations:
                                [1] [Smith et al., 2020, Example Paper Title]
                                [2] [Jones & Brown, 2019, Another Paper Title]

                                For numbered citations, keep them as is:
                                [1] [Smith et al., 2020, Example Paper Title]
                                [2] [Jones & Brown, 2019, Another Paper Title]

                                For author-year citations, format them as:
                                [Smith et al., 2020, Example Paper Title]
                                [Jones & Brown, 2019, Another Paper Title]

                                Make sure to:
                                1. Include ALL citations from the paper
                                2. Keep the exact format shown above
                                3. Include the year in the citation
                                4. Include the full paper title
                                5. Each citation should be on a new line
                                6. Start each citation with '[' and end with ']'
                                7. For numbered citations, keep the number in brackets
                                8. IMPORTANT: Preserve the exact author format from the paper:
                                - Keep "et al." exactly as it appears
                                - Keep "&" between authors exactly as it appears
                                - Keep all author names and their order exactly as they appear
                                - Do not modify or simplify author lists
                                9. Do not add or remove any punctuation or formatting from the original citations
                            """
                },
                {
                    "type": "document_url",
                    "document_url": pdf_url
                }
            ]
        }
    ]

    chat_response = client.chat.complete(
        model=model,
        messages=messages
    )

    data = chat_response.choices[0].message.content

    # Split the response into lines
    lines = data.strip().split('\n')

    # Extract title
    title = None
    citations = []
    in_citations_section = False

    for line in lines:
        line = line.strip()
        if not line:  # Skip empty lines
            continue
            
        if line.startswith('Title:'):
            title = line.replace('Title:', '').strip()
        elif line == 'Citations:':
            in_citations_section = True
        elif in_citations_section and line.startswith('[') and line.endswith(']'):
            # Handle both numbered and author-year citations
            citation_text = line[1:-1]  # Remove the outer '[' and ']'
            
            # Check if it's a numbered citation
            number_match = re.match(r'^(\d+)\]\s*\[(.*)$', citation_text)
            if number_match:
                # It's a numbered citation
                citation_number = number_match.group(1)
                citation_content = number_match.group(2)
                
                # Extract year from the citation content
                year_match = re.search(r',\s*(\d{4}[a-z]?),\s*', citation_content)
                year = year_match.group(1) if year_match else None
                
                if year_match:
                    # Find the position of the comma after the year
                    year_end_pos = year_match.end()
                    # Split at the first comma after the year
                    citation = citation_content[:year_end_pos-1].strip()  # -1 to remove the comma
                    paper_title = citation_content[year_end_pos:].strip()
                    citations.append({
                        'citation_number': citation_number,
                        'citation': citation,
                        'paper_title': paper_title,
                        'year': year
                    })
            else:
                # It's an author-year citation
                # First extract the year from the citation
                year_match = re.search(r',\s*(\d{4}[a-z]?),\s*', citation_text)
                year = year_match.group(1) if year_match else None
                
                if year_match:
                    # Find the position of the comma after the year
                    year_end_pos = year_match.end()
                    # Split at the first comma after the year
                    citation = citation_text[:year_end_pos-1].strip()  # -1 to remove the comma
                    paper_title = citation_text[year_end_pos:].strip()
                    citations.append({
                        'citation': citation,
                        'paper_title': paper_title,
                        'year': year
                    })

    return title, citations

def extract_citations_with_context(pdf_url: str):
    """
    Extract citations and their surrounding paragraph context from each page of a PDF document.
    Stops processing when it reaches the references section.
    
    Args:
        pdf_url (str): URL of the PDF document to process
        
    Returns:
        dict: Dictionary containing page numbers as keys and their citations with context as values
    """
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": pdf_url
        },
        include_image_base64=True
    )
    
    page_citations_with_context = {}
    
    for page in ocr_response.pages:
        # Check if we've reached the references section
        if re.search(r'(?i)^\s*(References|Citations|Appendix|Bibliography)\s*$', page.markdown):
            print("\nReached references section. Stopping processing.")
            break
            
        # Split text into paragraphs (assuming paragraphs are separated by double newlines)
        paragraphs = page.markdown.split('\n')
        
        page_citations = []
        
        for paragraph in paragraphs:
            # Find numbered citations like [1], [2], etc.
            numbered_citations = re.findall(r'\[(\d+)\]', paragraph)
            
            # Find author-year citations like (Author, Year)
            author_year_citations = re.findall(r'\(([^)]+?,\s*\d{4})\)', paragraph)
            
            if numbered_citations or author_year_citations:
                citation_context = {
                    'paragraph': paragraph.strip(),
                    'numbered_citations': [f"[{num}]" for num in numbered_citations],
                    'author_year_citations': [f"({citation})" for citation in author_year_citations]
                }
                page_citations.append(citation_context)
        
        page_citations_with_context[page.index + 1] = page_citations
    
    return page_citations_with_context
