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

    def add_to_library(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Add multiple records to the library table, skipping any that have matching titles.
        
        Args:
            records (List[Dict]): List of dictionaries containing record data to insert
            
        Returns:
            Dict[str, List[Dict]]: Dictionary containing lists of added and skipped records
        """
        try:
            added_records = []
            skipped_records = []
            
            for record in records:
                existing = self.client.table("library") \
                    .select("*") \
                    .eq("title", record["title"]) \
                    .execute()
                
                if not existing.data:
                    result = self.client.table("library").insert(record).execute()
                    added_records.append(result.data[0])
                else:
                    skipped_records.append(record)
            
            return {
                "added": added_records,
                "skipped": skipped_records
            }
        except Exception as e:
            logging.error(f"Error adding records to library: {e}")
            raise