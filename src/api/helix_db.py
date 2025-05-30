import json
from helix import Client, Query

db = Client(local=True)

class CreateOriginNode(Query):
    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def query(self) -> list[any]:
        return [{"content": self.content}]
    def response(self, response):
        return response
    
class GetOriginNodes(Query):
    def __init__(self):
        super().__init__()
    def query(self):
        return [{}]
    def response(self, response):
        return response
    
class DropAllNodes(Query):
    def __init__(self):
        super().__init__()
    def query(self):
        return []
    def response(self, response):
        return response
