import os
from pinecone import Pinecone
from dotenv import load_dotenv
from typing import List, Dict, Any
import json

load_dotenv()

class PineconeManager:
    """
    A class to manage Pinecone operations including initialization, querying, and data upsertion.
    
    Attributes:
        client (Pinecone): The Pinecone client instance
        index (Index): The Pinecone index instance
        index_name (str): Name of the Pinecone index
    """
    
    def __init__(self, index_name: str = "paperal"):
        """
        Initialize the PineconeManager with client and index.
        
        Args:
            index_name (str): Name of the Pinecone index to use. Defaults to "paperal".
        """
        self.index_name = index_name
        self.client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = None
        self._initialize_index()
        
    def _initialize_index(self) -> None:
        """
        Initialize the Pinecone index. Creates a new index if it doesn't exist.
        """
        if not self.client.has_index(self.index_name):
            self.client.create_index_for_model(
                name=self.index_name,
                cloud="aws",
                region="us-east-1",
                embed={
                    "model": "llama-text-embed-v2",
                    "field_map": {
                        "text": "text"
                    }
                }
            )
        
        self.index = self.client.Index(
            host=os.getenv("INDEX_HOST")
        )
    
    def query(self, namespace: str, query: str) -> Dict[str, Any]:
        """
        Query the Pinecone index.
        
        Args:
            namespace (str): The namespace to query in
            query (str): The query string to search for
            
        Returns:
            Dict[str, Any]: Query results from Pinecone
        """
        if not self.index:
            raise ValueError("Index not initialized")
        
        return self.index.search(
            namespace=namespace, 
            query={
                "inputs": {"text": query}, 
                "top_k": 3
            },
            fields=["category", "chunk_text"]
        )
    
    def upsert_records(self, namespace: str, data: List[Dict[str, Any]]) -> bool:
        """
        Upsert records into the Pinecone index.
        
        Args:
            namespace (str): The namespace to upsert records into
            data (List[Dict[str, Any]]): List of records to upsert
            
        Returns:
            bool: True if upsert was successful
            
        Raises:
            ValueError: If index is not initialized
        """
        if not self.index:
            raise ValueError("Index not initialized")
        
        self.index.upsert_records(namespace, data)
        return True

    def delete_records(self, namespace: str) -> bool:
        """
        Delete all records from the Pinecone index.
        
        Args:
            namespace (str): The namespace to delete records from
            
        Returns:
            bool: True if deletion was successful
        """
        self.index.delete(delete_all=True, namespace=namespace)
        return True

if __name__ == "__main__":
    pinecone_manager = PineconeManager()
    pinecone_manager.delete_records("library")
