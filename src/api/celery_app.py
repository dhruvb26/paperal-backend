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
    """
    try:
        logger.info("Starting Celery task process_urls_task")
        result = asyncio.run(process_urls(urls, strategy="langchain"))
        
        pinecone_manager = PineconeManager()
        supabase_manager = SupabaseManager()

        for item in result:
            if item:
                try:
                    metadata = asyncio.run(extract_metadata(item["info"]))
                    lib_record_metadata = {
                        "file_url": item["url"],
                        "authors": metadata["authors"],
                        "year": metadata["year"],
                        "citations": metadata["citations"]
                    }

                    if "vector_data" in item:
                        for vector in item["vector_data"]:
                            vector["file_url"] = item["url"]
                            vector["citation"] = metadata["citations"].get("in_text", "")
                        
                        try:
                            pinecone_manager.upsert_records("library", item["vector_data"])
                        except Exception as e:
                            logger.info(f"Error upserting records to Pinecone: {str(e)}")

                    lib_record = {
                        "title": metadata["title"],
                        "description": metadata["description"],
                        "metadata": lib_record_metadata
                    }
                    supabase_manager.add_to_library([lib_record])
                except Exception as e:
                    logger.info(f"Error processing item: {str(e)}")
        
        return {"status": "success", "processed_urls": len(urls)}

    except Exception as e:
        logger.info(f"Error in Celery task process_urls_task: {str(e)}")
        raise


celery_app.conf.timezone = 'UTC'
celery_app.conf.enable_utc = True

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    enable_utc=True,
)