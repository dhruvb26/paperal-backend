from typing import List
from pydantic import BaseModel, Field
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings

def remove_lucene_chars(text: str) -> str:
    """Remove special Lucene characters from text."""
    special_chars = ['+', '-', '&', '|', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\']
    for char in special_chars:
        text = text.replace(char, ' ')
    return text

class Entities(BaseModel):
    """Identifying information about entities."""
    names: List[str] = Field(
        ...,
        description="All the person, organization, or business entities that appear in the text",
    )

class GraphRetriever:
    def __init__(self, graph, llm=None):
        self.graph = graph
        self.llm = llm or ChatOpenAI(temperature=0, model_name="gpt-4-0125-preview")
        
        # Create entity extraction chain
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are extracting organization and person entities from the text."),
            ("human", "Use the given format to extract information from the following input: {question}"),
        ])
        self.entity_chain = prompt | self.llm.with_structured_output(Entities)
        
        # Create fulltext index if it doesn't exist
        self.graph.query(
            "CREATE FULLTEXT INDEX entity IF NOT EXISTS FOR (e:__Entity__) ON EACH [e.id]"
        )
        
        # Setup vector search
        self.vector_index = Neo4jVector.from_existing_graph(
            OpenAIEmbeddings(),
            search_type="hybrid",
            node_label="Document",
            text_node_properties=["text"],
            embedding_node_property="embedding"
        )

    def generate_full_text_query(self, input: str) -> str:
        """Generate a full-text search query with fuzzy matching."""
        full_text_query = ""
        words = [el for el in remove_lucene_chars(input).split() if el]
        for word in words[:-1]:
            full_text_query += f" {word}~2 AND"
        full_text_query += f" {words[-1]}~2"
        return full_text_query.strip()

    def structured_retriever(self, question: str) -> str:
        """Collect the neighborhood of entities mentioned in the question."""
        result = ""
        entities = self.entity_chain.invoke({"question": question})
        for entity in entities.names:
            response = self.graph.query(
                """CALL db.index.fulltext.queryNodes('entity', $query, {limit:2})
                YIELD node,score
                CALL {
                  MATCH (node)-[r:!MENTIONS]->(neighbor)
                  RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output
                  UNION
                  MATCH (node)<-[r:!MENTIONS]-(neighbor)
                  RETURN neighbor.id + ' - ' + type(r) + ' -> ' +  node.id AS output
                }
                RETURN output LIMIT 50
                """,
                {"query": self.generate_full_text_query(entity)},
            )
            result += "\n".join([el['output'] for el in response])
        return result

    def hybrid_retriever(self, question: str) -> str:
        """Combine structured and unstructured data retrieval."""

        structured_data = self.structured_retriever(question)
        unstructured_data = [el.page_content for el in self.vector_index.similarity_search(question)]
        final_data = f"""Structured data:
                        {structured_data}
                        Unstructured data:
                        {"#Document ".join(unstructured_data)}
                """
        return final_data

    def create_rag_chain(self):
        """Create the final RAG chain combining retrieval and generation."""
        template = """Answer the question based only on the following context:
                        
                    {context}

                    Question: {question}
                """
        
        prompt = ChatPromptTemplate.from_template(template)

        chain = (
            RunnableParallel(
                {
                    "context": lambda x: self.hybrid_retriever(x["question"]),
                    "question": RunnablePassthrough(),
                }
            )
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        return chain 