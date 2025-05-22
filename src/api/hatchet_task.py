from hatchet_sdk import Context, Hatchet, ClientConfig
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
from utils import process_urls
from helpers import PineconeManager, SupabaseManager, extract_metadata
import asyncio
import logging

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Hatchet with config
hatchet = Hatchet(debug=True)

class UrlInput(BaseModel):
    urls: List[str]

class UrlResult(BaseModel):
    url: str
    supabase_success: bool = False
    pinecone_success: bool = False
    error: str | None = None

class TaskResult(BaseModel):
    status: str
    processed_urls: int
    results: Dict[str, Any]

@hatchet.task(name="ProcessUrlsTask", input_validator=UrlInput)
async def process_urls_task(input: UrlInput, ctx: Context) -> Dict[str, Any]:
    """
    Hatchet task to process URLs in the background, handling each URL as it completes
    
    Args:
        input: UrlInput containing list of URLs to process
    Returns:
        Dict containing:
        - status: Overall task status
        - processed_urls: Number of URLs processed
        - results: Detailed success/failure info for each URL
    """
    try:
        logger.info("Starting Hatchet task process_urls_task")
        logger.info(f"Processing {len(input.urls)} URLs")
        
        logger.info("Initializing Pinecone and Supabase managers")
        pinecone_manager = PineconeManager()
        supabase_manager = SupabaseManager()

        results_tracking = {
            "total": len(input.urls),
            "successful": [],
            "failed": []
        }

        async for item in process_urls(input.urls, strategy="langchain"):
            if item:
                try:
                    url = item["url"]
                    logger.info(f"Processing URL: {url}")
                    url_result = {"url": url, "supabase_success": False, "pinecone_success": False, "error": None}
                    
                    logger.info(f"Extracting metadata for {url}")
                    metadata = await extract_metadata(item["info"])
                    if not metadata["year"] or not metadata["title"] or not metadata["description"] or not metadata["authors"]:
                        logger.info(f"No meaningful metadata found for {url}")
                        results_tracking["failed"].append({
                            "url": url,
                            "supabase_success": False,
                            "pinecone_success": False,
                            "error": "No meaningful metadata found"
                        })
                        continue

                    lib_record_metadata = {
                        "file_url": url,
                        "authors": metadata["authors"],
                        "year": metadata["year"],
                        "citations": metadata["citations"]
                    }

                    lib_record = {
                        "title": metadata["title"],
                        "description": metadata["description"],
                        "metadata": lib_record_metadata
                    }
                    
                    logger.info(f"Adding record to Supabase library for {url}")
                    supabase_result = supabase_manager.add_to_library([lib_record])
                    url_result["supabase_success"] = bool(supabase_result.get("added"))
                    logger.info(f"Supabase add result: {url_result['supabase_success']}")
                
                    supabase_record_id = supabase_result["added"][0].get("id")
                    logger.info(f"Got Supabase record ID: {supabase_record_id}")
                    
                    logger.info(f"Preparing vector data for Pinecone for {url}")
                    for vector in item["vector_data"]:
                        vector["file_url"] = url
                        vector["citation"] = metadata["citations"].get("in_text", "")
                        vector["library_id"] = supabase_record_id
                    
                    try:
                        logger.info(f"Upserting records to Pinecone for {url}")
                        pinecone_manager.upsert_records("library", item["vector_data"])
                        url_result["pinecone_success"] = True
                        logger.info(f"Pinecone records upserted successfully for {url}")
                    except Exception as e:
                        error_msg = f"Error upserting records to Pinecone: {str(e)}"
                        logger.error(error_msg)
                        url_result["error"] = error_msg
                            
                    if url_result["supabase_success"] and url_result["pinecone_success"]:
                        logger.info(f"Successfully processed {url}")
                        results_tracking["successful"].append(url_result)
                    else:
                        logger.info(f"Failed to fully process {url}")
                        results_tracking["failed"].append(url_result)
                            
                except Exception as e:
                    error_msg = f"Error processing item: {str(e)}"
                    logger.error(error_msg)
                    results_tracking["failed"].append({
                        "url": item["url"],
                        "supabase_success": False,
                        "pinecone_success": False,
                        "error": error_msg
                    })

        logger.info(f"Task completed. Processed {len(input.urls)} URLs. Successful: {len(results_tracking['successful'])}, Failed: {len(results_tracking['failed'])}")
        return {
            "status": "success",
            "processed_urls": len(input.urls),
            "results": results_tracking
        }

    except Exception as e:
        error_msg = f"Error in Hatchet task process_urls_task: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg,
            "results": {
                "total": len(input.urls),
                "successful": [],
                "failed": [{"url": url, "error": error_msg} for url in input.urls]
            }
        }

