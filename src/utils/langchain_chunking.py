from langchain_text_splitters import TokenTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
import tiktoken
import uuid
import re

def clean_text(text: str) -> str:
    """Clean text by removing special characters and normalizing whitespace."""
    text = re.sub(r'[\u201c\u201d]', '"', text)
    text = re.sub(r'[\u2018\u2019]', "'", text)
    
    text = re.sub(r'[\u2012\u2013\u2014\u2015]', '-', text)
    
    text = re.sub(r'\s+', ' ', text)
    
    text = ''.join(char for char in text if char.isprintable())
    
    return text.strip()

def get_token_length(text: str) -> int:
    """Get the length of text in tokens using the same encoding as the splitter."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_chunks(file_path: str):

    info = ""

    text_splitter = TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=512, 
        chunk_overlap=100,
        length_function=get_token_length,
    )

    loader = PyMuPDFLoader(file_path, mode="page",extract_tables="markdown")

    docs = loader.load()

    split_docs = text_splitter.split_documents(docs)

    final_chunks = []

    for i, doc in enumerate(split_docs): 
        split_text = text_splitter.split_text(doc.page_content)

        split_text = [clean_text(text.replace("\n", " ")) for text in split_text]

        if i < 5: 
            info += doc.page_content

        for text in split_text:
            if text.strip(): 
                final_chunks.append({
                    "_id": str(uuid.uuid4()),
                    # "chunk_length": get_token_length(text),
                    "text": text,
                })

    return info, final_chunks
