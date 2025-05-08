from ..celery_app import celery_app
from utils import process_urls
from helpers import PineconeManager, SupabaseManager, extract_metadata
import logging
import asyncio

@celery_app.task(bind=True, name='api.tasks.process_urls_task')
def process_urls_task(self, urls: list[str]):
    """
    Celery task to process URLs in the background
    
    Args:
        urls: List of URLs to process
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("Starting Celery task process_urls_task")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(process_urls(urls))
        
        if not result:
            logger.info("Failed to process URLs in Celery task")
            return None

        pinecone_manager = PineconeManager()
        supabase_manager = SupabaseManager()

        for item in result:
            if item:
                try:
                    metadata = loop.run_until_complete(extract_metadata(item["info"]))

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
                        "title": item["title"],
                        "description": metadata["description"],
                        "metadata": lib_record_metadata
                    }
                    supabase_manager.add_to_library([lib_record])
                except Exception as e:
                    logger.info(f"Error processing item: {str(e)}")
        
        return {"status": "success", "processed_urls": len(urls)}

    except Exception as e:
        logger.info(f"Error in Celery task process_urls_task: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
    finally:
        loop.close()
