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
from utils import has_date_in_content
import logging

load_dotenv()

async def process_urls(urls: list[str]):
    """
    Process multiple document URLs concurrently using Chunkr
    
    Args:
        urls: List of URLs to process
    Returns:
        List of processed data for each URL
    """
    try:
        chunkr = Chunkr(api_key=os.getenv("CHUNKR_API_KEY"))
        
        chunk_config = Configuration(
            chunk_processing=ChunkProcessing(
                ignore_headers_and_footers=False,
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
            task = asyncio.create_task(process_single_url(chunkr, url, chunk_config))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    except Exception as e:
        logging.error(f"Error processing URLs: {str(e)}")
        return []
    finally:
        await chunkr.close()

async def process_single_url(chunkr: Chunkr, url: str, config: Configuration):
    """
    Process a single URL and return the processed data
    
    Args:
        chunkr: Chunkr instance
        url: URL to process
        config: Chunk configuration
    Returns:
        Dictionary containing processed chunks and metadata
    """
    try:
        task = await chunkr.upload(url, config)
        
        if task.output and task.output.chunks:
            chunks = task.output.chunks
            
            vector_data = [
                {
                    "_id": chunk.chunk_id,
                    "text": chunk.embed,
                    "category": str(chunk.chunk_length)
                }
                for chunk in chunks
            ]

            title = ""
            info = ""
            
            for chunk in chunks[:3]:
                for segment in chunk.segments:
                    info += segment.content
                    if segment.segment_type == "Title":
                        title = segment.content
            
            for chunk in chunks[:15]:
                for segment in chunk.segments:
                    if segment.segment_type == "PageFooter" and has_date_in_content(segment.content):
                        info += segment.content
                        break

            return {
                "url": url,
                "title": title,
                "info": info,
                "vector_data": vector_data,
                "chunks": chunks
            }
            
    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")
        return None