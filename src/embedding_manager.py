import faiss
import numpy as np
from typing import List, Dict
import requests
import os
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


class EmbeddingManager:
    """
    Manages text chunking, embedding generation using LMStudio, and FAISS operations.
    """

    def __init__(
        self,
        model: str = "text-embedding-nomic-embed-text-v1.5",
        lmstudio_url: str = "http://127.0.0.1:1234/v1/embeddings",
        knowledgebase_dir: str = "knowledgebase",
    ):
        self.model = model
        self.lmstudio_url = lmstudio_url
        self.knowledgebase_dir = knowledgebase_dir
        self.index_file = os.path.join(knowledgebase_dir, "faiss.index")
        self.metadata_file = os.path.join(knowledgebase_dir, "metadata.json")
        self.index = faiss.IndexFlatL2(768)  # Assuming 768-dimensional embeddings
        self.metadata = []
        self.index_lock = Lock()  # Lock for thread-safe FAISS operations

        if not os.path.exists(knowledgebase_dir):
            os.makedirs(knowledgebase_dir)

        self.load_knowledgebase()

    def chunk_text(
        self, text: str, chunk_size: int = 300, overlap: int = 100
    ) -> List[str]:
        """Splits text into overlapping chunks based on words."""
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += chunk_size - overlap
        return chunks

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generates an embedding for the given text using LMStudio."""
        payload = {"model": self.model, "input": [text]}
        response = requests.post(self.lmstudio_url, json=payload)

        if response.status_code != 200:
            raise ValueError(f"Embedding generation failed: {response.text}")

        embedding = response.json()["data"][0]["embedding"]
        return np.array(embedding, dtype="float32")

    def add_to_index_and_metadata(self, embedding: np.ndarray, meta: Dict):
        """Thread-safe addition of embedding and metadata."""
        with self.index_lock:
            self.index.add(np.array([embedding]))
            self.metadata.append(meta)

    def add_embeddings(self, chunks: List[str], metadata: List[Dict]):
        """Generates and adds embeddings to the FAISS index."""
        with ThreadPoolExecutor() as executor:
            embeddings = list(executor.map(self.generate_embedding, chunks))

        # Add embeddings and metadata sequentially for thread safety
        for embedding, meta in zip(embeddings, metadata):
            self.add_to_index_and_metadata(embedding, meta)

        self.save_knowledgebase()

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Searches the FAISS index for the most similar chunks."""
        query_embedding = self.generate_embedding(query)
        distances = np.empty((1, top_k), dtype=np.float32)
        _, indices = self.index.search(np.array([query_embedding]), top_k)
        results = [self.metadata[idx] for idx in indices[0] if idx != -1]
        return results, distances

    def save_knowledgebase(self):
        """Saves the FAISS index and metadata to files."""
        with self.index_lock:
            faiss.write_index(self.index, self.index_file)
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f)

    def load_knowledgebase(self):
        """Loads the FAISS index and metadata from files if they exist."""
        if os.path.exists(self.index_file):
            self.index = faiss.read_index(self.index_file)
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, "r") as f:
                self.metadata = json.load(f)

    def extend_from_structured_json(self, json_file_path: str):
        """Adds embeddings from a JSON file where each item is a chunk."""
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        with open(json_file_path, "r") as f:
            data = json.load(f)

        chunks = [item["question"] for item in data]
        metadata = [
            {
                "question": item["question"],
                "query": item["query"],
                "answer": item["answer"],
            }
            for item in data
        ]

        chunks.extend([item["query"] for item in data])
        metadata.extend(
            [
                {
                    "question": item["question"],
                    "query": item["query"],
                    "answer": item["answer"],
                }
                for item in data
            ]
        )

        chunks.extend([item["answer"] for item in data])
        metadata.extend(
            [
                {
                    "question": item["question"],
                    "query": item["query"],
                    "answer": item["answer"],
                }
                for item in data
            ]
        )

        self.add_embeddings(chunks, metadata)

    def extend_knowledge_base(self):
        """
        Prompts the user for a file path, reads the text content or JSON content, then embeds and stores it.
        """
        file_path = input("Please enter the file path to add to the knowledge base: ")
        if not os.path.isfile(file_path):
            print("Invalid file path. Skipping extension of the knowledge base.")
            return

        if file_path.endswith(".txt"):
            self._extend_from_text_file(file_path)
        elif file_path.endswith(".json"):
            self.extend_from_structured_json(file_path)
        else:
            print("Unsupported file type. Please provide a .txt or .json file.")

    def _extend_from_text_file(self, file_path: str):
        """
        Reads text content from a file, chunks it, generates embeddings, and stores them.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        if not text.strip():
            print("File is empty. Skipping extension of the knowledge base.")
            return

        # Example metadata detail (could be more dynamic)
        metadata = [{"content": chunk} for chunk in self.chunk_text(text)]
        metadata = metadata[:500]  # Limit metadata to 500 chunks
        self.add_embeddings([m["content"] for m in metadata], metadata)
        print("Knowledge base extended successfully.")
