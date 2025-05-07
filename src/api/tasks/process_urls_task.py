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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(process_urls(urls))
        
        if not result:
            logging.error("Failed to process URLs in Celery task")
            return None

        pinecone_manager = PineconeManager()
        supabase_manager = SupabaseManager()

        for item in result:
            if item and "vector_data" in item:
                pinecone_manager.upsert_records("library", item["vector_data"])
            
            if item:
                metadata = loop.run_until_complete(extract_metadata(item["info"]))
                lib_record = {
                    "title": item["title"],
                    "description": metadata["description"],
                    "metadata": {
                        "file_url": item["url"],
                        "authors": metadata["authors"],
                        "year": metadata["year"],
                        "citations": metadata["citations"]
                    }
                }
                supabase_manager.add_to_library([lib_record])
        
        return {"status": "success", "processed_urls": len(urls)}

    except Exception as e:
        logging.error(f"Error in Celery task process_urls_task: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
    finally:
        loop.close()
