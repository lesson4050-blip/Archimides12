import asyncio
import json
import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2


class IconFinderService:
    def __init__(self):
        self.collection_name = "icons"
        self.client = chromadb.PersistentClient(
            path="chroma", settings=Settings(anonymized_telemetry=False)
        )
        print("Initializing icons collection...")
        self._initialize_icons_collection()
        print("Icons collection initialized.")

    def _initialize_icons_collection(self):
        self.embedding_function = ONNXMiniLM_L6_V2()
        self.embedding_function.DOWNLOAD_PATH = "chroma/models"
        self.embedding_function._download_model_if_not_exists()
        try:
            print(f"Attempting to get collection '{self.collection_name}'...")
            self.collection = self.client.get_collection(
                self.collection_name, embedding_function=self.embedding_function
            )
            print("Collection found.")
        except Exception as e:
            print(f"Collection not found or error ({e}). Rebuilding...")
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icons_path = os.path.join(base_dir, "assets", "icons.json")
            print(f"Loading icons from {icons_path}...")
            with open(icons_path, "r", encoding="utf-8") as f:
                icons = json.load(f)

            documents = []
            ids = []
            metadatas = []

            for i, each in enumerate(icons["icons"]):
                doc_text = f"{each['name']} {each['tags']}"
                documents.append(doc_text)
                ids.append(each["name"])
                metadatas.append({"style": each["style"], "name": each["name"]})

            print(f"Prepared {len(documents)} icons for indexing.")
            if documents:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"},
                )
                print("Collection created. Starting batch indexing...")
                # ChromaDB batch limit is usually 5461, we have ~9000
                batch_size = 2000
                for i in range(0, len(documents), batch_size):
                    end = min(i + batch_size, len(documents))
                    print(f"Indexing batch {i} to {end}...")
                    self.collection.add(
                        documents=documents[i:end],
                        ids=ids[i:end],
                        metadatas=metadatas[i:end]
                    )
                print("Indexing complete.")

    async def search_icons(self, query: str, style: str = "bold", k: int = 1):
        # Default to bold since that's what we have in static
        result = await asyncio.to_thread(
            self.collection.query,
            query_texts=[query],
            n_results=k,
            where={"style": style}
        )
        if not result["ids"] or not result["ids"][0]:
            # Try to search without style filter as fallback
            result = await asyncio.to_thread(
                self.collection.query,
                query_texts=[query],
                n_results=k
            )
            if not result["ids"] or not result["ids"][0]:
                return []
            
        # The files in static are only in 'bold' directory and named {name}-bold.svg
        urls = []
        for i, name in enumerate(result["ids"][0]):
            # Force bold since it's the only one we have
            urls.append(f"/static/icons/bold/{name}-bold.svg")
        return urls


ICON_FINDER_SERVICE = IconFinderService()
