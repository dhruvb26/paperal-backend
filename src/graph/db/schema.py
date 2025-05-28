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
                    year: $year
                })
            """, authors=json.dumps(node["authors"]), title=node["title"], year=node["year"])

def add_origin_nodes(chunks_content: dict, task_id: str):
    with driver.session() as session:
        session.run("""
            CREATE (t:Task {
                task_id: $task_id
            })
        """, task_id=task_id)
        
        for chunk_id, content in chunks_content.items():
            session.run("""
                MATCH (t:Task {task_id: $task_id})
                CREATE (o:Origin {
                    content: $content,
                    chunk_id: $chunk_id
                })
                CREATE (t)-[:HAS_ORIGIN]->(o)
            """, content=content, chunk_id=chunk_id, task_id=task_id)

if __name__ == "__main__":

    with open("sample/citations.json", "r") as f:
        citations = json.load(f)

    add_cited_nodes(citations)

    # with open("sample/chunks.json", "r") as f:
    #     raw_data = json.load(f)
    
    # total_chunks = raw_data["output"]["chunks"]
    # task_id = raw_data["task_id"]
    # chunks_content = {}

    # for chunk in total_chunks:
    #     chunk_id = chunk["chunk_id"]
    #     segments_text = []
        
    #     for segment in chunk["segments"]:
    #         segments_text.append(segment["content"])
        
    #     chunks_content[chunk_id] = "\n".join(segments_text)

    # add_origin_nodes(chunks_content, task_id)
