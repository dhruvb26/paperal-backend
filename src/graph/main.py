import getpass
import os
import logging
from typing import Literal
import json
from langgraph.graph import MessagesState, StateGraph, END
from langchain.chat_models import init_chat_model
from graph.vector_search import VectorSearchTool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from utils import serialize_tool_result, format_structured_response
from models import PaperState, GradeDocuments

response_model = init_chat_model("openai:gpt-4o", temperature=0.4)
grader_model = init_chat_model("openai:gpt-4.1", temperature=0)

vector_search_tool = VectorSearchTool()

GRADE_PROMPT = (
    "You are a grader assessing relevance of a retrieved text chunks to the previous sentences written so far in a research paper draft. \n "
    "Here are the retrieved text chunks: \n\n {context} \n\n"
    "Here are the previous sentences: {question} \n"
    "Give a binary score 'yes' or 'no' score to indicate whether the text chunks are relevant."
)

def _set_env(key: str):
    if key not in os.environ:
        logging.debug(f"Setting environment variable: {key}")
        os.environ[key] = getpass.getpass(f"{key}:")

_set_env("GOOGLE_API_KEY")
_set_env("OPENAI_API_KEY")

def generate_question_for_rag(content: str) -> str:
    """
    Generate a specific question for vector search based on the previous sentences.
    
    Args:
        content (str): The previous 2-3 sentences from the research paper
        
    Returns:
        str: A focused question for vector search
    """
    messages = [
        SystemMessage(content="You are an academic writing assistant that generates search queries for vector search. Given the previous 2-3 sentences from a research paper draft, generate a specific question that will help find relevant chunks of text to continue the academic writing. Only return the question itself."),
        HumanMessage(content=content)
    ]
    
    response = response_model.invoke(messages)
    return response.content

def evaluate_rag_necessity(content: str) -> bool:
    """
    Evaluate whether the next sentence in the academic writing requires citation.
    
    Args:
        content (str): The previous 2-3 sentences from the research paper
        
    Returns:
        bool: True if citation is needed, False otherwise
    """
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
    return result

def execute_tool_call(tool_call):
    """Execute a tool call and return its result."""
    tool_name = tool_call["function"]["name"]
    tool_args = json.loads(tool_call["function"]["arguments"])
    
    if tool_name == "vector_search":
        result = vector_search_tool._run(**tool_args)
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
    content = state["messages"][0].content
    search_query = generate_question_for_rag(content)
    
    model = response_model.bind_tools([vector_search_tool])
    initial_response = model.invoke([
        SystemMessage(content="Use the vector_search tool with the given query."),
        HumanMessage(content=f"Using the following search query: '{search_query}")
    ])
    
    retrieved_documents = []
    
    if hasattr(initial_response, 'additional_kwargs') and 'tool_calls' in initial_response.additional_kwargs:
        for tool_call in initial_response.additional_kwargs['tool_calls']:
            tool_result = execute_tool_call(tool_call)
            if tool_result:
                serialized_tool_result = serialize_tool_result(tool_result)
                retrieved_documents.append(serialized_tool_result)
        
        retrieved_context = json.dumps(retrieved_documents)
        
        return {"messages": state["messages"] + [AIMessage(content=retrieved_context)]}

    return {"messages": state["messages"] + [AIMessage(content="No relevant documents found.")]}

def generate_response_with_rag(state: MessagesState):
    """
    Generates the next sentence for the academic paper using the retrieved documents
    
    Args:
        state (MessagesState): The current conversation state with previous sentences and retrieved documents
    
    Returns:
        MessagesState: Updated state with the generated next sentence
    """
    previous_sentences = state["messages"][0].content
    retrieved_context = state["messages"][-1].content

    try:
        context_data = json.loads(retrieved_context)
        citation_info = {}
        if isinstance(context_data, list) and context_data:
            doc = context_data[0]
            results = doc.get("results", [])
            first_hit = results[0] if results else None
            if first_hit and isinstance(first_hit, dict):
                fields = first_hit.get("fields", {})
                citation_info = {
                    "file_url": fields.get("file_url"),
                    "citation": fields.get("citation"),
                    "context": fields.get("text")
                }
    except (json.JSONDecodeError, TypeError, KeyError):
        citation_info = None
    
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
    
    structured_response = format_structured_response(response.content, citation_info)
    
    return {"messages": state["messages"] + [AIMessage(content=json.dumps(structured_response))]}

def generate_normal_response(state: MessagesState):
    """
    Generates the next sentence for the academic paper without using retrieved documents
    
    Args:
        state (MessagesState): The current conversation state with previous sentences
    
    Returns:
        MessagesState: Updated state with the generated next sentence
    """
    previous_sentences = state["messages"][0].content
    
    response = response_model.invoke([
        SystemMessage(content="""You are an academic writing assistant.
        Generate ONLY the next single sentence that continues the academic writing based on the previous sentences.
        Your sentence should maintain the academic tone and flow naturally from the previous sentences.
        Generate ONLY ONE sentence - do not write an entire paragraph or multiple sentences."""),
        HumanMessage(content=previous_sentences)
    ])
    
    structured_response = format_structured_response(response.content)
    return {"messages": state["messages"] + [AIMessage(content=json.dumps(structured_response))]}

def check_relevance(
    state: MessagesState,
) -> Literal["generate_with_rag", "generate_normal"]:
    """Determine whether the retrieved documents are relevant to the previous sentences written so far."""
    previous_sentences = state["messages"][0].content
    retrieved_context = state["messages"][-1].content
    
    if retrieved_context == "No relevant documents found.":
        return {"check_relevance": "generate_normal"}

    prompt = GRADE_PROMPT.format(question=previous_sentences, context=retrieved_context)
    response = (
        grader_model
        .with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score

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
    content = state["paper_content"]
    
    if evaluate_rag_necessity(content):
        search_query = generate_question_for_rag(content)
        
        model = response_model.bind_tools([vector_search_tool])
        initial_response = model.invoke([
            SystemMessage(content="You are a helpful research assistant. Use the vector_search tool to find relevant papers and incorporate them into your response."),
            HumanMessage(content=f"Using the following search query: '{search_query}', find relevant papers to help answer: {content}")
        ])
        
        retrieved_documents = []
        
        if hasattr(initial_response, 'additional_kwargs') and 'tool_calls' in initial_response.additional_kwargs:
            for tool_call in initial_response.additional_kwargs['tool_calls']:
                tool_result = execute_tool_call(tool_call)
                if tool_result:
                    serialized_tool_result = serialize_tool_result(tool_result)
                    retrieved_documents.append(serialized_tool_result)
            
            retrieved_context = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(retrieved_documents)
            
            messages = [
                SystemMessage(content="""You are a helpful research assistant. 
                You MUST use the information from the retrieved documents to answer the user's question.
                Base your response primarily on the provided documents.
                Include specific citations and references to the retrieved content.
                Be accurate and comprehensive in using the retrieved information."""),
                HumanMessage(content=f"QUESTION: {content}\n\nRETRIEVED DOCUMENTS:\n{retrieved_context}")
            ]
            
            response = response_model.invoke(messages)
    else:
        response = response_model.invoke([
            SystemMessage(content="You are a helpful research assistant. Provide a general response without specific citations."),
            HumanMessage(content=content)
        ])
    
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

async def query_graph(query: str):
    """
    Build the query workflow graph
    
    Returns:
        StateGraph: The configured workflow graph
    """
    workflow = await build_rag_graph()
    
    result = workflow.invoke({"messages": [HumanMessage(content=query)]})
    
    return result["messages"][-1].content