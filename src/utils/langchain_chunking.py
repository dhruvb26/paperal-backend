import os
import uuid
import json
import tiktoken
from getpass import getpass
from langchain_openai import ChatOpenAI
from utils.text import clean_split_text
from langchain_text_splitters import TokenTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders.parsers.images import LLMImageBlobParser

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass("OpenAI API key =")

def get_token_length(text: str) -> int:
    """Get the length of text in tokens using the same encoding as the splitter."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_chunks(file_path: str, save_chunks: bool = False, chunk_size: int = 512, chunk_overlap: int = 100):

    info = ""

    text_splitter = TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        length_function=get_token_length,
    )

    loader = PyMuPDFLoader(file_path, 
                           mode="page",
                           extract_tables="markdown",
                           images_inner_format="markdown-img",
                           images_parser=LLMImageBlobParser(model=ChatOpenAI(model="gpt-4o-mini", max_tokens=1024)))

    docs = loader.load()

    split_docs = text_splitter.split_documents(docs)

    final_chunks = []

    for i, doc in enumerate(split_docs): 
        split_text = text_splitter.split_text(doc.page_content)

        split_text = [clean_split_text(text.replace("\n", " ")) for text in split_text]

        if i < 5: 
            info += doc.page_content

        for text in split_text:
            if text.strip(): 
                final_chunks.append({
                    "_id": str(uuid.uuid4()),
                    # "chunk_length": get_token_length(text),
                    "text": text,
                })

    if save_chunks:
        with open("sample/langchain_chunks.json", "w") as f:
            json.dump(final_chunks, f)

    return info, final_chunks
