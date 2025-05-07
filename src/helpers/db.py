import logging
import os
from typing import List, Optional, Dict, Any
from openai import OpenAI
from supabase.client import create_client
from dotenv import load_dotenv
from models.library import LibraryRecord

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True
)

class SupabaseManager:
    """
    A class to manage Supabase operations including initialization and data operations.
    
    Attributes:
        client (Client): The Supabase client instance
        openai_client (OpenAI): The OpenAI client instance
    """
    
    def __init__(self):
        """
        Initialize the SupabaseManager with Supabase and OpenAI clients.
        """
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            self.client = create_client(supabase_url, supabase_key)
        except Exception as e:
            logging.error(f"Error creating Supabase client: {e}")
            raise

        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            self.openai_client = OpenAI(api_key=openai_api_key)
        except Exception as e:
            logging.error(f"Error creating OpenAI client: {e}")
            raise

    def query_metadata(self, metadata_filters: Dict[str, str], user_id: Optional[str] = None):
        """
        Query the library table based on multiple metadata fields and values.
        
        Args:
            metadata_filters (Dict[str, str]): Dictionary of metadata fields and their values to match
                Example: {"category": "research", "year": "2024"}
            user_id (Optional[str]): The user ID to filter by
            
        Returns:
            Response from Supabase query containing matching records
        """
        query = self.client.from_("library").select("*")
    
        for field, value in metadata_filters.items():
            field = f"metadata->>{field}"
            query = query.eq(field, value)
        
        if user_id:
            query = query.eq("user_id", user_id)
        else:
            query = query.is_("user_id", None)
        
        return query.execute()

    def add_to_library(self, records: List[LibraryRecord]) -> None:
        """
        Add multiple records to the library table.
        
        Args:
            records (List[LibraryRecord]): List of LibraryRecord objects to insert
        """
        try:
            records_data = [record.model_dump() for record in records]
            self.client.table("library").insert(records_data).execute()
            logging.info(f"Successfully added {len(records)} records to library")
        except Exception as e:
            logging.error(f"Error adding records to library: {e}")
            raise

