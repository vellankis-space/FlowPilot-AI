
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from firecrawl import Firecrawl

load_dotenv(override=True)

# 1. Initialize Clients
# ---------------------
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")
if not firecrawl_api_key:
    raise ValueError("FIRECRAWL_API_KEY not found in .env file")

# Print a portion of the key to verify it's loaded correctly
print(f"Attempting to use OpenAI key: {openai_api_key[:5]}...{openai_api_key[-4:]}")

firecrawl_client = Firecrawl(api_key=firecrawl_api_key)
openai_client = OpenAI(api_key=openai_api_key)
chroma_client = chromadb.PersistentClient(path="backend/vector_store")

# 2. Crawl the Website
# --------------------
# The URL to start crawling from
crawl_url = 'https://docs.mermaidchart.com/mermaid-oss/intro/index.html'

print(f"Starting crawl for {crawl_url}...")

# Perform the crawl
crawled_data = firecrawl_client.crawl(
    url=crawl_url,
    include_paths=['/mermaid-oss/'], # Focus on the open-source documentation section
    scrape_options={
        'onlyMainContent': True,
        'format': 'markdown',
        'maxAge': 86400000  # Use cached data if less than 1 day old
    },
    limit=50
)

if not crawled_data or not crawled_data.data:
    print("No data was crawled or crawl failed. Exiting.")
    exit()

print(f"Crawl completed. Found {len(crawled_data.data)} documents.")

# 3. Embed and Store in Vector DB
# --------------------------------
# Get or create the collection for Mermaid syntax
collection = chroma_client.get_or_create_collection(name="mermaid_syntax")

print("Embedding documents and storing them in the vector database...")

# Process and add documents to the collection
for doc in crawled_data.data:
    content = doc.markdown
    metadata = doc.metadata
    source_url = metadata.source_url

    if not content or not source_url:
        continue

    # Create embedding
    try:
        response = openai_client.embeddings.create(
            input=content,
            model="text-embedding-ada-002"
        )
        embedding = response.data[0].embedding

        # Add to collection
        collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"source": source_url}],
            ids=[source_url] # Use the unique source URL as the ID
        )
        print(f"  - Embedded and stored: {source_url}")
    except Exception as e:
        print(f"Error embedding document {source_url}: {e}")

print("\nMermaid syntax vector database has been built successfully from crawled data.")
