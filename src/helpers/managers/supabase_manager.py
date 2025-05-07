import logging
import os
from typing import List, Optional, Dict
from supabase.client import create_client
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:
    """
    A class to manage Supabase operations including initialization and data operations.
    
    Attributes:
        client (Client): The Supabase client instance
    """
    
    def __init__(self):
        """
        Initialize the SupabaseManager with Supabase client.
        """
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            self.client = create_client(supabase_url, supabase_key)
        except Exception as e:
            logging.error(f"Error creating Supabase client: {e}")
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
            
        Raises:
            Exception: If there's an error executing the query
        """
        try:
            query = self.client.from_("library").select("*")
        
            for field, value in metadata_filters.items():
                field = f"metadata->>{field}"
                query = query.eq(field, value)
            
            if user_id:
                query = query.eq("user_id", user_id)
            else:
                query = query.is_("user_id", None)
            
            result = query.execute()
            return result
        except Exception as e:
            logging.error(f"Error querying library with filters {metadata_filters}: {e}")
            raise

    def add_to_library(self, records: List[Dict]) -> None:
        """
        Add multiple records to the library table.
        
        Args:
            records (List[Dict]): List of dictionaries containing record data to insert
        """
        try:
            self.client.table("library").insert(records).execute()
        except Exception as e:
            logging.error(f"Error adding records to library: {e}")
            raise