from chunkr_ai import Chunkr
from chunkr_ai.models import (
    Configuration,
    SegmentProcessing,
    GenerationConfig,
    EmbedSource,
    ChunkProcessing,
    Tokenizer,
)
from dotenv import load_dotenv
import os
import asyncio
from helpers.store_pinecone import PineconeManager
from helpers.db import SupabaseManager
from models.library import LibraryRecord
import json
load_dotenv()

async def process_urls(urls: list[str]):
    """
    Process multiple document URLs concurrently using Chunkr
    
    Args:
        urls: List of URLs to process
    """
    try:
        chunkr = Chunkr(api_key=os.getenv("CHUNKR_API_KEY"))
        pinecone_manager = PineconeManager()
        supabase_manager = SupabaseManager()
        
        chunk_config = Configuration(
           chunk_processing=ChunkProcessing(
                tokenizer=Tokenizer.CL100K_BASE
            ),
            segment_processing=SegmentProcessing(
                Table=GenerationConfig(
                    llm="Summarize the key trends in this table including any context from legends or surrounding text",
                    embed_sources=[EmbedSource.LLM, EmbedSource.MARKDOWN],
                    extended_context=True
                ),
                Picture=GenerationConfig(
                    llm="Summarize the understanding of this image with the context of the surrounding text",
                    embed_sources=[EmbedSource.LLM, EmbedSource.MARKDOWN],
                    extended_context=True,
                ),
            ),
        )

        tasks = []
        for url in urls:
            task = asyncio.create_task(process_single_url(chunkr, url, chunk_config, pinecone_manager, supabase_manager))
            tasks.append(task)
        
        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"Error processing URLs: {str(e)}")
    finally:
        await chunkr.close()

async def process_single_url(chunkr: Chunkr, url: str, config: Configuration, pinecone_manager: PineconeManager, supabase_manager: SupabaseManager):
    """
    Process a single URL with error handling
    
    Args:
        chunkr: Chunkr instance
        url: URL to process
        config: Chunk configuration
    """
    try:
        task = await chunkr.upload(url, config)
        
        # Wait for task completion and get output
        if task.output and task.output.chunks:
            chunks = task.output.chunks
            
            data = [
                {
                    "_id": chunk.chunk_id,
                    "text": chunk.embed,
                    "category": str(chunk.chunk_length)
                }
                for chunk in chunks
            ]

            print(len(data))
            print(data[0])

            pinecone_manager.upsert_records(namespace="library", data=data)

            for chunk in chunks:
                if hasattr(chunk, 'segments'):
                    for segment in chunk.segments:
                        if segment.segment_type == "Title":
                            title = segment.content
                            break
                    if title != url:  
                        break

            metadata = {
                "file_url": url,
                "year": 2024,
                "authors": ["John Doe", "Jane Smith"],
                "citations": {
                    "in_text": "example citation",
                }
            }
    
            supabase_manager.add_to_library(LibraryRecord(
                title=title,  
                description=url,
                metadata=metadata,
            ))

            return data
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return None

if __name__ == "__main__":
    
    # open chunks.json
    with open("../sample/chunks.json", "r") as f:
        raw_data = json.load(f)

    chunks = raw_data["output"]["chunks"]

    for chunk in chunks: 
        segments = chunk["segments"]

        for segment in segments:
            if segment["segment_type"] == "Title":
                print(segment["content"])
