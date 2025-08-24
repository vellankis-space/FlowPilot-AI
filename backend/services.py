
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def search_rpa_actions(query: str, n_results: int = 10):
    """
    Searches the RPA actions vector database for a given query.

    Args:
        query: The search query.
        n_results: The number of results to return.

    Returns:
        A list of search results.
    """
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Create embedding for the query
    response = client.embeddings.create(
        input=query,
        model="text-embedding-ada-002"
    )
    query_embedding = response.data[0].embedding

    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(path="backend/vector_store")

    # Get the collection
    collection = chroma_client.get_collection(name=collection_name)

    # Query the collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["metadatas", "documents", "distances"]
    )
    return results
