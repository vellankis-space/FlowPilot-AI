

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

# Define a function to process and add actions to a collection
def process_and_add_actions(collection_name, actions_data, tool_name):
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    actions_to_add = []
    if tool_name == "Automation Anywhere":
        for package in actions_data:
            for action in package.get('actions', []):
                actions_to_add.append({
                    "tool": tool_name,
                    "action": action.get('name', 'Unknown Action'),
                    "description": action.get('description', ''),
                    "package": package.get('package', '')
                })
    else:
        actions_to_add = actions_data

    for action in actions_to_add:
        content = f"Tool: {action.get('tool', tool_name)}\nAction: {action.get('action', 'Unknown Action')}\nDescription: {action.get('description', '')}"
        if 'parameters' in action:
            for param in action.get('parameters', []):
                content += f"\nParameter: {param.get('name', '')} - {param.get('description', '')}"

        response = client.embeddings.create(
            input=content,
            model="text-embedding-ada-002"
        )
        embedding = response.data[0].embedding

        collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"tool": action.get('tool', tool_name)}],
            ids=[action.get('action', 'Unknown Action')]
        )
    print(f"Collection '{collection_name}' has been built successfully.")

# Load RPA actions from JSON files
script_dir = os.path.dirname(__file__)
power_automate_path = os.path.join(script_dir, 'data', 'power_automate_actions_detailed.json')
automation_anywhere_path = os.path.join(script_dir, 'data', 'automation_anywhere_actions_detailed.json')

with open(power_automate_path, 'r') as f:
    power_automate_actions = json.load(f)

with open(automation_anywhere_path, 'r') as f:
    automation_anywhere_actions = json.load(f)

# Process for Power Automate
process_and_add_actions("power_automate", power_automate_actions, "Power Automate")

# Process for Automation Anywhere
process_and_add_actions("automation_anywhere", automation_anywhere_actions, "Automation Anywhere")

print("Vector database has been built successfully.")



