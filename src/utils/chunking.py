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
# from utils.text import get_pdf_page_count
from utils.langchain_chunking import get_chunks
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

async def process_urls(urls: list[str], strategy: str = "chunkr"):
    """
    Process multiple document URLs one at a time using Chunkr
    
    Args:
        urls: List of URLs to process
    Returns:
        Async generator yielding processed data for each URL as it completes
    """
    try:
        logging.info(f"Starting to process {len(urls)} URLs using strategy: {strategy}")
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

        for url in urls:
            result = await process_single_url(chunkr, url, chunk_config, strategy)
            if result is not None:
                yield result
            logging.info(f"Completed processing URL: {url}")

    except Exception as e:
        logging.error(f"Error processing URLs: {str(e)}", exc_info=True)
    finally:
        await chunkr.close()
        logging.info("Closed Chunkr client")

async def process_single_url(chunkr: Chunkr, url: str, config: Configuration, strategy: str):
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
        logging.info(f"Processing URL: {url}")
            
        if strategy == "chunkr":
            logging.info(f"Using Chunkr strategy for {url}")
            task = await chunkr.upload(url, config)
            if task.output and task.output.chunks:
                chunks = task.output.chunks
                logging.info(f"Successfully extracted {len(chunks)} chunks from {url}")
                
                vector_data = [
                    {
                        "_id": chunk.chunk_id,
                        "text": chunk.embed,
                    }
                    for chunk in chunks
                ]

                title = ""
                info = ""
                
                for chunk in chunks[:15]:
                    for segment in chunk.segments:
                        if segment.segment_type == "Title":
                            title = segment.content
                            logging.info(f"Found title: {title}")
                        elif (segment.segment_type == "PageFooter" or segment.segment_type == "PageHeader") or has_date_in_content(segment.content):
                            info += segment.content
                            break

                logging.info(f"Completed processing {url} with Chunkr strategy")
                return {
                    "url": url,
                    "title": title,
                    "info": info,
                    "vector_data": vector_data,
                    "chunks": chunks
                }
        else:
            logging.info(f"Using alternative chunking strategy for {url}")
            info, chunks = get_chunks(url)
            logging.info(f"Successfully processed {url} with alternative strategy")

            return {
                "url": url,
                "info": info,
                "vector_data": chunks
            }
            
    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
        return None