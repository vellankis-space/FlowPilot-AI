

import os
import json
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="backend/vector_store")

# Create or get a collection
collection = chroma_client.get_or_create_collection(name="rpa_actions")

# Load RPA actions from JSON file
with open('backend/data/power_automate_actions_detailed.json', 'r') as f:
    rpa_actions = json.load(f)

# Process and add documents to the collection
for action in rpa_actions:
    # Create a single string with all the information
    content = f"Tool: {action['tool']}\nAction: {action['action']}\nDescription: {action['description']}"
    if 'parameters' in action:
        for param in action['parameters']:
            content += f"\nParameter: {param['name']} - {param['description']}"

    # Create embedding
    response = client.embeddings.create(
        input=content,
        model="text-embedding-ada-002"
    )
    embedding = response.data[0].embedding

    # Add to collection
    collection.add(
        embeddings=[embedding],
        documents=[content],
        metadatas=[{"tool": action['tool']}],
        ids=[action['action']]
    )

print("Vector database has been built successfully.")



