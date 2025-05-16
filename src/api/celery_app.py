from celery import Celery
from dotenv import load_dotenv
import os
from utils import process_urls
from helpers import PineconeManager, SupabaseManager, extract_metadata
import asyncio
import logging
from celery.utils.log import get_task_logger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

celery_app = Celery(
    'paperal-celery',
    broker=os.getenv('REDIS_URL'),
    backend=os.getenv('REDIS_URL'),
)

logger = get_task_logger(__name__)

@celery_app.task(name='api.tasks.process_urls_task')
def process_urls_task(urls: list[str]):
    """
    Celery task to process URLs in the background
    
    Args:
        urls: List of URLs to process
    Returns:
        Dict containing:
        - status: Overall task status
        - processed_urls: Number of URLs processed
        - results: Detailed success/failure info for each URL
    """
    try:
        logger.info("Starting Celery task process_urls_task")
        result = asyncio.run(process_urls(urls, strategy="langchain"))
        
        pinecone_manager = PineconeManager()
        supabase_manager = SupabaseManager()

        results_tracking = {
            "total": len(urls),
            "successful": [],
            "failed": []
        }

        for item in result:
            if item:
                try:
                    url = item["url"]
                    url_result = {"url": url, "supabase_success": False, "pinecone_success": False, "error": None}
                    
                    metadata = asyncio.run(extract_metadata(item["info"]))
                    if not metadata["year"] or not metadata["title"] or not metadata["description"] or not metadata["authors"]:
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
                    
                    supabase_result = supabase_manager.add_to_library([lib_record])
                    url_result["supabase_success"] = bool(supabase_result.get("added"))
                
                    supabase_record_id = supabase_result["added"][0].get("id")
                    
                    for vector in item["vector_data"]:
                        vector["file_url"] = url
                        vector["citation"] = metadata["citations"].get("in_text", "")
                        vector["library_id"] = supabase_record_id
                    
                    try:
                        pinecone_manager.upsert_records("library", item["vector_data"])
                        url_result["pinecone_success"] = True
                        logger.info(f"Pinecone records upserted successfully.")
                    except Exception as e:
                        error_msg = f"Error upserting records to Pinecone: {str(e)}"
                        logger.error(error_msg)
                        url_result["error"] = error_msg
                            
                    if url_result["supabase_success"] and url_result["pinecone_success"]:
                        results_tracking["successful"].append(url_result)
                    else:
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
            else:
                results_tracking["failed"].append({
                    "url": "Unknown URL",
                    "supabase_success": False,
                    "pinecone_success": False,
                    "error": "Failed to process URL"
                })
        
        return {
            "status": "success",
            "processed_urls": len(urls),
            "results": results_tracking
        }

    except Exception as e:
        error_msg = f"Error in Celery task process_urls_task: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg,
            "results": {
                "total": len(urls),
                "successful": [],
                "failed": [{"url": url, "error": error_msg} for url in urls]
            }
        }


celery_app.conf.timezone = 'UTC'
celery_app.conf.enable_utc = True

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    enable_utc=True,
)