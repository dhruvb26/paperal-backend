import google.generativeai as genai
import os
import asyncio
from dotenv import load_dotenv
from utils import parse_json_safely
import logging
from models import TopicMetadata, DocumentMetadata

load_dotenv()

def read_prompt(prompt_file: str, **kwargs) -> str:
    """
    Read a prompt from a file and format it with the given kwargs
    
    Args:
        prompt_file: Path to the prompt file
        kwargs: Keyword arguments to format the prompt with
        
    Returns:
        Formatted prompt string
    """
    try:
        with open(prompt_file, 'r') as f:
            prompt = f.read()
            
        prompt = prompt.replace('{', '{{').replace('}', '}}')
        
        for key in kwargs:
            prompt = prompt.replace('{{' + key + '}}', '{' + key + '}')
            
        return prompt.format(**kwargs)
    except Exception as e:
        logging.error(f"Error reading prompt: {str(e)}")
        return ""

async def make_gemini_call(prompt: str, model_name: str = 'gemini-1.5-flash-002') -> str:
    """
    Make a generic call to Gemini API
    
    Args:
        prompt: The prompt to send to Gemini
        model_name: Name of the Gemini model to use
        
    Returns:
        Response text from Gemini
    """
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(model_name)
    response = await model.generate_content_async(prompt)
    
    return response.text.strip()
async def extract_metadata(doc_info: str) -> DocumentMetadata:
    """
    Extract structured metadata from document info using Gemini
    
    Args:
        doc_info: Text content from document chunks
        
    Returns:
        DocumentMetadata containing title, authors and citation
    """
    try:
        prompt = f"""Based on the following document excerpt, extract the title, authors, a short description, year of publication, and create an APA style in-text citation.
                    Return the information in a valid JSON format with these exact keys: title, description, authors (as list), citations.in_text, year

                    If you cannot determine any field with high confidence, use null for that field.

                    Document excerpt:
                    {doc_info}

                    Example output format:
                    {{
                        "title": "The Impact of AI on Modern Society",
                        "description": "The Impact of AI on Modern Society is a paper that discusses the impact of AI on modern society. It is a paper that was published in 2024.",
                        "authors": ["Smith, J.", "Jones, K."],
                        "citations": {{
                            "in_text": "(Smith & Jones, 2024)"
                        }},
                        "year": "2024"
                    }}
                    """
        response_text = await make_gemini_call(prompt)
        
        metadata = parse_json_safely(response_text)
        if metadata is None:
            raise ValueError("No valid JSON found in response")
        
        if not all(key in metadata for key in ["title", "description", "authors", "citations"]) or \
           "in_text" not in metadata.get("citations", {}):
            raise ValueError("Missing required fields in Gemini response")
            
        return metadata
        
    except Exception as e:
        logging.error(f"Error extracting metadata with Gemini: {str(e)}")
        return DocumentMetadata(
            title="",
            description="",
            year="",
            authors=[],
            citations={
                "in_text": ""
            }
        )

async def extract_research_topic(user_query: str) -> TopicMetadata:
    """
    Extract research topic information from a user query using Gemini
    
    Args:
        user_query: The user's research paper query/request
        
    Returns:
        TopicMetadata containing main topic, sub-topics, and research question
    """
    try:
        prompt = f"""
                You are a research topic extraction assistant. Your task is to analyze the user's query and extract the main research topic they want to write about.

                Please identify the core research topic and provide it in the following JSON format:

                {
                    "main_topic": "The primary research topic which will also be the title of the research paper",
                    "sub_topics": ["List of related sub-topics or aspects to explore"],
                    "research_question": "A well-formulated research question based on the topic"
                }

                User Query: {user_query}

                Provide only the JSON response without any additional text or explanation. 
                """
        response_text = await make_gemini_call(prompt)

        topic_data = parse_json_safely(response_text)
        if topic_data is None:
            raise ValueError("No valid JSON found in response")
        
        if not all(key in topic_data for key in ["main_topic", "sub_topics", "research_question"]):
            raise ValueError("Missing required fields in Gemini response")
        
        return topic_data
        
    except Exception as e:
        logging.error(f"Error extracting research topic with Gemini: {str(e)}")
        return TopicMetadata(
            main_topic="",
            sub_topics=[],
            research_question=""
        )

if __name__ == "__main__":
    asyncio.run(extract_research_topic("What is the main topic of the paper?"))