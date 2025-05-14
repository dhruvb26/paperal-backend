import os
from pinecone import Pinecone
from dotenv import load_dotenv
from typing import List, Dict, Any

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
        self.sparse_index_name = f"{index_name}-sparse"
        self.client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = None
        self.sparse_index = None
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
        
        if not self.client.has_index(self.sparse_index_name):
            self.client.create_index_for_model(
                name=self.sparse_index_name,
                cloud="aws",
                region="us-east-1",
                embed={
                    "model": "pinecone-sparse-english-v0",
                    "field_map": {
                        "text": "text"
                    }
                }
            )

        dense_index_info = self.client.describe_index(name=self.index_name)
        sparse_index_info = self.client.describe_index(name=self.sparse_index_name)
        
        self.index = self.client.Index(
            host=dense_index_info["host"]
        )

        self.sparse_index = self.client.Index(
            host=sparse_index_info["host"]
        )

    def merge_chunks(self, h1: Dict[str, Any], h2: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Get the unique hits from two search results and return them as single array of {'_id', 'text'} dicts, printing each dict on a new line."""
        
        # deduplicate by _id
        deduped_hits = {hit['_id']: hit for hit in h1['result']['hits'] + h2['result']['hits']}.values()

        # sort by _score descending
        sorted_hits = sorted(deduped_hits, key=lambda x: x['_score'], reverse=True)

        result = [{'_id': hit['_id'], 'fields': hit['fields']} for hit in sorted_hits]

        reranked_results = self.rerank_results(result, query)

        return reranked_results
    

    def rerank_results(self, merged_results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        
        original_data = {hit['_id']: hit['fields'] for hit in merged_results}
        rerank_documents = [{"id": hit['_id'], "text": hit['fields']['text']} for hit in merged_results]
    
        reranked_results = self.client.inference.rerank(
            model="bge-reranker-v2-m3",
            query=query,
            documents=rerank_documents,
            rank_fields=["text"],
            top_n=10,
            return_documents=True,
            parameters={
                "truncate": "END"
            }
        )

        reranked_results = [{
            '_id': hit['document']['id'], 
            'fields': {
                'text': hit['document']['text'],
                **{k: v for k, v in original_data[hit['document']['id']].items() if k != 'text'}
            }
        } for hit in reranked_results.data]

        return reranked_results
    
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
        
        dense_hits = self.index.search(
            namespace=namespace, 
            query={
                "inputs": {"text": query}, 
                "top_k": 3
            },
        )

        sparse_hits = self.sparse_index.search(
            namespace=namespace,
            query={
                "inputs": {"text": query},
                "top_k": 3
            },
        )

        return self.merge_chunks(dense_hits, sparse_hits, query)
    
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
        
        batch_size = 96
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            self.index.upsert_records(namespace, batch)

            self.sparse_index.upsert_records(namespace, batch)
        
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
        self.sparse_index.delete(delete_all=True, namespace=namespace)

        return True