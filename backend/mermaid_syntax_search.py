"""
Tool for searching Mermaid.js syntax examples from a vector database collection.
"""
import os
from chromadb import Client
from chromadb.config import Settings

MERMAID_COLLECTION_PATH = os.path.join(os.path.dirname(__file__), "data", "mermaid_collection")

def search_mermaid_syntax(query: str, top_k: int = 1):
    """
    Search the Mermaid syntax collection for the most relevant syntax snippet.
    Args:
        query (str): The diagram type or structure to search for.
        top_k (int): Number of top results to return.
    Returns:
        List of Mermaid.js syntax strings.
    """
    client = Client(Settings(persist_directory=MERMAID_COLLECTION_PATH))
    collection = client.get_collection("mermaid_syntax")
    results = collection.query(query_texts=[query], n_results=top_k)
    return [doc for doc in results["documents"][0]]