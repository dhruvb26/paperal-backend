import getpass
import os
import logging
from typing import TypedDict, Literal
import json
import asyncio
from langgraph.graph import MessagesState, StateGraph, END
from langchain.chat_models import init_chat_model
from graph.vector_search import VectorSearchTool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

response_model = init_chat_model("openai:gpt-4o", temperature=0)
vector_search_tool = VectorSearchTool()

GRADE_PROMPT = (
    "You are a grader assessing relevance of a retrieved text chunks to the previous sentences written so far in a research paper draft. \n "
    "Here are the retrieved text chunks: \n\n {context} \n\n"
    "Here are the previous sentences: {question} \n"
    "Give a binary score 'yes' or 'no' score to indicate whether the text chunks are relevant."
)

class GradeDocuments(BaseModel):
    """Grade documents using a binary score for relevance check."""

    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )

grader_model = init_chat_model("openai:gpt-4.1", temperature=0)

def _set_env(key: str):
    if key not in os.environ:
        logging.info(f"Setting environment variable: {key}")
        os.environ[key] = getpass.getpass(f"{key}:")

_set_env("OPENAI_API_KEY")

class PaperState(TypedDict):
    paper_content: str

def generate_question_for_rag(content: str) -> str:
    """
    Generate a specific question for vector search based on the previous sentences.
    
    Args:
        content (str): The previous 2-3 sentences from the research paper
        
    Returns:
        str: A focused question for vector search
    """
    logging.info("Generating RAG question for content")
    messages = [
        SystemMessage(content="You are an academic writing assistant that generates search queries for vector search. Given the previous 2-3 sentences from a research paper draft, generate a specific question that will help find relevant chunks of text to continue the academic writing."),
        HumanMessage(content=content)
    ]
    
    response = response_model.invoke(messages)
    logging.debug(f"Generated question: {response.content}")
    return response.content

def evaluate_rag_necessity(content: str) -> bool:
    """
    Evaluate whether the next sentence in the academic writing requires citation.
    
    Args:
        content (str): The previous 2-3 sentences from the research paper
        
    Returns:
        bool: True if citation is needed, False otherwise
    """
    logging.info("Evaluating RAG necessity")
    messages = [
        SystemMessage(content="""You are an academic writing assistant that determines if the next sentence needs citation.
        Analyze the previous 2-3 sentences and determine if the next sentence should include a citation to support the ongoing discussion.
        Return 'true' if the next sentence would benefit from citing relevant research papers.
        Return 'false' if the next sentence can continue the flow without specific citations.
        Only return 'true' or 'false' without any other text."""),
        HumanMessage(content=content)
    ]
    
    response = response_model.invoke(messages)
    result = response.content.lower().strip() == 'true'
    logging.info(f"RAG necessity evaluation result: {result}")
    return result

def execute_tool_call(tool_call):
    """Execute a tool call and return its result."""
    logging.info(f"Executing tool call: {tool_call['function']['name']}")
    tool_name = tool_call["function"]["name"]
    tool_args = json.loads(tool_call["function"]["arguments"])
    
    if tool_name == "vector_search":
        result = vector_search_tool._run(**tool_args)
        logging.info(f"Tool call result: {result}")
        return result
    return None

def retrieve_relevant_documents(state: MessagesState):
    """
    Retrieves documents relevant to continuing the academic writing
    
    Args:
        state (MessagesState): The current conversation state with previous sentences
    
    Returns:
        MessagesState: Updated state with retrieved documents
    """
    logging.info("Retrieving relevant documents")
    content = state["messages"][0].content
    search_query = generate_question_for_rag(content)
    
    model = response_model.bind_tools([vector_search_tool])
    logging.info(f"Executing search with query: {search_query}")
    initial_response = model.invoke([
        SystemMessage(content="Use the vector_search tool with the given query."),
        HumanMessage(content=f"Using the following search query: '{search_query}")
    ])
    
    retrieved_documents = []
    
    if hasattr(initial_response, 'additional_kwargs') and 'tool_calls' in initial_response.additional_kwargs:
        logging.info("Processing tool calls from initial response")
        
        for tool_call in initial_response.additional_kwargs['tool_calls']:
            tool_result = execute_tool_call(tool_call)
            if tool_result:
                retrieved_documents.append(str(tool_result))
                logging.info(f"Retrieved document content added to context")
        
        # Combine all retrieved documents into consolidated context
        retrieved_context = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(retrieved_documents)
        logging.info(f"Consolidated {len(retrieved_documents)} documents for context")
        
        return {"messages": state["messages"] + [AIMessage(content=retrieved_context)]}
    
    # If no documents were retrieved, return empty context
    return {"messages": state["messages"] + [AIMessage(content="No relevant documents found.")]}

def generate_response_with_rag(state: MessagesState):
    """
    Generates the next sentence for the academic paper using the retrieved documents
    
    Args:
        state (MessagesState): The current conversation state with previous sentences and retrieved documents
    
    Returns:
        MessagesState: Updated state with the generated next sentence
    """
    logging.info("Generating next sentence with citation")
    previous_sentences = state["messages"][0].content
    retrieved_context = state["messages"][-1].content

    print(f"Previous sentences: {previous_sentences}")
    print(f"Retrieved context: {retrieved_context}")
    
    messages = [
        SystemMessage(content="""You are an academic writing assistant. 
        Generate ONLY the next single sentence that continues the academic writing based on the previous sentences.
        Use the information from the retrieved documents to craft a well-cited sentence.
        Your sentence should maintain the academic tone and flow naturally from the previous sentences.
        Include a citation in the form (Author, Year) if you're using specific information from the documents.
        Generate ONLY ONE sentence - do not write an entire paragraph or multiple sentences."""),
        HumanMessage(content=f"PREVIOUS SENTENCES: {previous_sentences}\n\nRETRIEVED DOCUMENTS:\n{retrieved_context}")
    ]
    
    response = response_model.invoke(messages)
    logging.info("Generated next sentence with citation")
    
    return {"messages": state["messages"] + [response]}

def generate_normal_response(state: MessagesState):
    """
    Generates the next sentence for the academic paper without using retrieved documents
    
    Args:
        state (MessagesState): The current conversation state with previous sentences
    
    Returns:
        MessagesState: Updated state with the generated next sentence
    """
    logging.info("Generating next sentence without citation")
    previous_sentences = state["messages"][0].content
    
    response = response_model.invoke([
        SystemMessage(content="""You are an academic writing assistant.
        Generate ONLY the next single sentence that continues the academic writing based on the previous sentences.
        Your sentence should maintain the academic tone and flow naturally from the previous sentences.
        Generate ONLY ONE sentence - do not write an entire paragraph or multiple sentences."""),
        HumanMessage(content=previous_sentences)
    ])
    
    logging.info("Next sentence generation complete")
    return {"messages": state["messages"] + [response]}

def check_relevance(
    state: MessagesState,
) -> Literal["generate_with_rag", "generate_normal"]:
    """Determine whether the retrieved documents are relevant to the previous sentences written so far."""
    logging.info("Starting document relevance check")
    previous_sentences = state["messages"][0].content
    retrieved_context = state["messages"][-1].content
    
    if retrieved_context == "No relevant documents found.":
        logging.info("No documents found, generating normal response")
        return {"check_relevance": "generate_normal"}
    
    print(f"Previous sentences: {previous_sentences}")
    print(f"Retrieved context: {retrieved_context}")

    # final_context = retrieved_context["results"]

    prompt = GRADE_PROMPT.format(question=previous_sentences, context=retrieved_context)
    response = (
        grader_model
        .with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score
    logging.info(f"Document relevance check result: {score}")

    if score == "yes":
        return {"check_relevance": "generate_with_rag"}
    else:
        return {"check_relevance": "generate_normal"}

def generate_query_or_respond(state: PaperState):
    """
    Analyzes the context and either generates a cited response or a direct answer.

    Given the previous context from a research paper draft, this function:
    1. Determines if the response requires citations
    2. If citations needed: Uses vector search to find and cite relevant papers
    3. If no citations needed: Generates a direct response
    
    Args:
        state (PaperState): The current conversation state containing messages

    Returns:
        dict: A dictionary with the 'messages' key containing the response
    """
    logging.info("Starting query/response generation")
    content = state["paper_content"]
    
    if evaluate_rag_necessity(content):
        logging.info("RAG determined necessary, generating search query")
        search_query = generate_question_for_rag(content)
        
        model = response_model.bind_tools([vector_search_tool])
        logging.info(f"Executing initial search with query: {search_query}")
        initial_response = model.invoke([
            SystemMessage(content="You are a helpful research assistant. Use the vector_search tool to find relevant papers and incorporate them into your response."),
            HumanMessage(content=f"Using the following search query: '{search_query}', find relevant papers to help answer: {content}")
        ])
        
        # Collect all retrieved documents
        retrieved_documents = []
        
        if hasattr(initial_response, 'additional_kwargs') and 'tool_calls' in initial_response.additional_kwargs:
            logging.info("Processing tool calls from initial response")
            
            for tool_call in initial_response.additional_kwargs['tool_calls']:
                tool_result = execute_tool_call(tool_call)
                if tool_result:
                    retrieved_documents.append(str(tool_result))
                    logging.info(f"Retrieved document content added to context")
            
            # Combine all retrieved documents into consolidated context
            retrieved_context = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(retrieved_documents)
            logging.info(f"Consolidated {len(retrieved_documents)} documents for context")
            
            # Create messages with explicit instructions to use retrieved content
            messages = [
                SystemMessage(content="""You are a helpful research assistant. 
                You MUST use the information from the retrieved documents to answer the user's question.
                Base your response primarily on the provided documents.
                Include specific citations and references to the retrieved content.
                Be accurate and comprehensive in using the retrieved information."""),
                HumanMessage(content=f"QUESTION: {content}\n\nRETRIEVED DOCUMENTS:\n{retrieved_context}")
            ]
            
            response = response_model.invoke(messages)
            logging.info("Generated response with explicit document context")
    else:
        logging.info("RAG not necessary, generating direct response")
        response = response_model.invoke([
            SystemMessage(content="You are a helpful research assistant. Provide a general response without specific citations."),
            HumanMessage(content=content)
        ])
    
    logging.info("Response generation complete")
    return {"messages": [response]}

async def build_rag_graph():
    """
    Build the RAG workflow graph with relevance checking
    
    Returns:
        StateGraph: The configured workflow graph
    """
    workflow = StateGraph(MessagesState)
    
    workflow.add_node("retrieve_documents", retrieve_relevant_documents)
    workflow.add_node("check_relevance", check_relevance)
    workflow.add_node("generate_with_rag", generate_response_with_rag)
    workflow.add_node("generate_normal", generate_normal_response)
    
    workflow.add_edge("retrieve_documents", "check_relevance")
    workflow.add_conditional_edges(
        "check_relevance",
        lambda x: x["check_relevance"],
        {
            "generate_with_rag": "generate_with_rag",
            "generate_normal": "generate_normal",
        },
    )
    workflow.add_edge("generate_with_rag", END)
    workflow.add_edge("generate_normal", END)
    
    workflow.set_entry_point("retrieve_documents")
    
    graph = workflow.compile()

    return graph

if __name__ == "__main__":
    logging.info("Starting main execution")
    workflow = asyncio.run(build_rag_graph())
    sample_query = "Our findings align with the hypothesis tested by Anthropic researchers, who observed that large language models exhibit a capacity for moral self-correction when given appropriate natural language prompts."
    result = workflow.invoke({"messages": [HumanMessage(content=sample_query)]})
    
    # Extract the model's response from the last message
    final_response = result["messages"][-1].content
    print("\nModel's Response:")
    print(final_response)
    
    logging.info("Main execution complete")