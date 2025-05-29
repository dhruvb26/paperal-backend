from neo4j import GraphDatabase
import json

URI = "neo4j+s://9495079e.databases.neo4j.io"
AUTH = ("neo4j", "8R-QJdAP1SBaMQUYlWyN9Nbs_6pALaij_qE88HW0vT8")

driver = GraphDatabase.driver(URI, auth=AUTH)

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()

def add_cited_nodes(cited_nodes: list):
    with driver.session() as session:
        for node in cited_nodes:
            session.run("""
                CREATE (c:Cited {
                    authors: $authors,
                    title: $title,
                    year: $year,
                    order: $order
                })
            """, authors=json.dumps(node["authors"]), title=node["title"], year=node["year"], order=node["order"])

def add_origin_nodes(chunks_data: dict, task_id: str):
    with driver.session() as session:
        session.run("""
            CREATE (t:Task {
                task_id: $task_id
            })
        """, task_id=task_id)
        
        for chunk_id, data in chunks_data.items():
            content = data["content"]
            citation_orders = data["citation_orders"]
            session.run("""
                MATCH (t:Task {task_id: $task_id})
                CREATE (o:Origin {
                    content: $content,
                    chunk_id: $chunk_id
                })
                CREATE (t)-[:HAS_ORIGIN]->(o)
                WITH o
                UNWIND $citation_orders AS order
                MATCH (c:Cited {order: toInteger(order)})
                CREATE (o)-[:CITED]->(c)
            """, content=content, chunk_id=chunk_id, task_id=task_id, citation_orders=citation_orders)

# if __name__ == "__main__":

#     with open("sample/local/citations.json", "r") as f:
#         citations = json.load(f)
    
#     for i, citation in enumerate(citations):
#         citation["order"] = i + 1

#     add_cited_nodes(citations)

#     with open("sample/chunkr/chunks.json", "r") as f:
#         raw_data = json.load(f)
    
#     total_chunks = raw_data["output"]["chunks"]
#     task_id = raw_data["task_id"]
#     chunks_data = {}

#     for chunk in total_chunks:
#         chunk_id = chunk["chunk_id"]
#         segments_text = []
#         citation_orders = []

#         for segment in chunk["segments"]:
#             segments_text.append(segment["content"])
#             if segment["llm"]:
#                 citation_orders.append(segment["llm"])

#         chunks_data[chunk_id] = {
#             "content": "\n".join(segments_text),
#             "citation_orders": [str(order.strip()) for c in citation_orders if c for order in c.strip("[]").split(",")]
#         }

#     add_origin_nodes(chunks_data, task_id)
