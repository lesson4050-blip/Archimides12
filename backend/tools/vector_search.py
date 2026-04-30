import chromadb
import os

class VectorSearchEngine:
    def __init__(self, db_dir=\"data/chroma_db\"):
        self.client = chromadb.PersistentClient(path=db_dir)
        self.collection = self.client.get_or_create_collection(\"code_symbols\")

    def add_symbol(self, name, kind, file_path, content):
        self.collection.add(documents=[content], metadatas=[{\"name\": name, \"kind\": kind, \"path\": file_path}], ids=[f\"{file_path}:{name}\"])
