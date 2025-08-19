

import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="backend/vector_store")

# Get the collection
collection = chroma_client.get_collection(name="rpa_actions")

def search_rpa_actions(query, n_results=1):
    # Create embedding for the query
    response = client.embeddings.create(
        input=query,
        model="text-embedding-ada-002"
    )
    query_embedding = response.data[0].embedding

    # Query the collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results

if __name__ == '__main__':
    # Example search
    search_query = "How to send an email?"
    search_results = search_rpa_actions(search_query)
    print("\n--- Search Results ---")
    print(search_results)

