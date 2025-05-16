from langchain_community.document_loaders import WikipediaLoader
from langchain_text_splitters import TokenTextSplitter
from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from .graph_retriever import GraphRetriever
from langchain_core.documents import Document
import os
import json

def setup_graph():
    """Setup and return the Neo4j graph with initial data."""
    # Initialize Neo4j connection
    graph = Neo4jGraph()
    
    # Load and process Wikipedia data
    raw_documents = WikipediaLoader(query="Elizabeth I").load()
    text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=24)
    documents = text_splitter.split_documents(raw_documents[:3])
    
    # Setup LLM and graph transformer
    llm = ChatOpenAI(temperature=0, model_name="gpt-4-0125-preview")
    llm_transformer = LLMGraphTransformer(llm=llm)
    
    # Extract and store graph data
    graph_documents = llm_transformer.convert_to_graph_documents(documents)
    graph.add_graph_documents(
        graph_documents,
        baseEntityLabel=True,
        include_source=True
    )
    
    return graph

def create_rag_chain():
    """Create and return the RAG chain."""
    # Setup graph and retriever
    # graph = setup_graph()
    graph = Neo4jGraph()
    retriever = GraphRetriever(graph)
    
    # Create and return the chain
    return retriever.create_rag_chain()

def convert_chunks_to_graph_documents(chunks):
    # Initialize Neo4j connection
    graph = Neo4jGraph()
    
    # Convert chunks to LangChain documents
    documents = []
    for chunk in chunks:
        # Extract content and metadata from your chunk format
        content = chunk.get('embed', '')  # or use the appropriate field from your chunks
        metadata = {
            'chunk_id': chunk.get('chunk_id'),
            'chunk_length': chunk.get('chunk_length'),
            # Add any other metadata you want to preserve
        }
        
        doc = Document(
            page_content=content,
            metadata=metadata
        )
        documents.append(doc)
    
    # Setup LLM and graph transformer
    llm = ChatOpenAI(temperature=0, model_name="gpt-4-0125-preview")
    llm_transformer = LLMGraphTransformer(llm=llm)
    
    # Convert to graph documents
    graph_documents = llm_transformer.convert_to_graph_documents(documents)
    
    # Add to Neo4j
    graph.add_graph_documents(
        graph_documents,
        baseEntityLabel=True,
        include_source=True
    )
    
    return graph

if __name__ == "__main__":
    # Example usage
    # chain = create_rag_chain()

    with open("src/sample/chunks.json", "r") as f:
        raw_data = json.load(f)

    graph = convert_chunks_to_graph_documents(raw_data["output"]["chunks"])
    
    # Test a question
    # result = chain.invoke({"question": "Which house did Elizabeth I belong to?"})
    # print(result)
    
    # Test a follow-up question
    # result = chain.invoke({
    #     "question": "When was she born?",
    #     "chat_history": [("Which house did Elizabeth I belong to?", "House Of Tudor")],
    # })
    # print(result)