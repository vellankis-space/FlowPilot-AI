from crewai import Agent, Task, Crew
from crewai.tools import tool
from crewai_tools import ScrapeWebsiteTool
from langchain_openai import ChatOpenAI
from backend.services import search_rpa_actions
from backend.diagram_generator import generate_mermaid_diagram # Added import

import json

import os
import logging
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# Configure logging to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("llm_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add this line to check if the API key is loaded
logger.info(f"OPENAI_API_KEY loaded: {bool(os.getenv('OPENAI_API_KEY'))}")

# Initialize the LLM model with OpenAI
llm = ChatOpenAI(
    model="gpt-5-nano-2025-08-07",
    temperature=1
)

# Add this line to check the llm object
logger.info(f"LLM object initialized: {llm is not None}")
logger.info(f"LLM model: {llm.model_name}")

@tool("rpa_actions_search")
def search_rpa_actions_tool(query: str) -> str:
    """Search for RPA actions in the vector database."""
    return search_rpa_actions(query)

# New tool for generating Mermaid syntax
@tool("generate_mermaid_diagram_tool")
def generate_mermaid_diagram_tool(nodes_json: str, edges_json: str) -> str:
    """
    Generates Mermaid.js syntax from a JSON representation of nodes and edges.
    Args:
        nodes_json: A JSON string representing the nodes of the diagram.
        edges_json: A JSON string representing the edges of the diagram.
    Returns:
        A string containing the Mermaid.js syntax.
    """
    nodes = json.loads(nodes_json)
    edges = json.loads(edges_json)
    return generate_mermaid_diagram(nodes, edges)

# Define the Requirement Structuring Agent
requirement_structuring_agent = Agent(
    role="Requirement Analyst",
    goal="Extract and enumerate all required automation steps from the user's query.",
    backstory=(
        "You are an expert in analyzing user requests for automation. "
        "You break down complex requests into clear, step-by-step tasks for an RPA workflow."
    ),
    llm=llm,
    allow_delegation=False,
    verbose=True
)

# Define the Tool Mapper Agent
tool_mapper_agent = Agent(
    role="Tool Mapper",
    goal="Translate high-level steps into a structured JSON format representing the workflow graph, specifically utilizing actions from the designated RPA toolset.",
    backstory=(
        "You are an expert in RPA tools and workflow design, with deep knowledge of specific platforms. You take a list of tasks and, using your expertise and access to the relevant toolset's actions, create a structured JSON representation of the workflow."
    ),
    llm=llm,
    tools=[search_rpa_actions_tool],
    allow_delegation=False,
    verbose=True
)

# Instantiate the ScrapeWebsiteTool
scrape_tool = ScrapeWebsiteTool()

# Define the Mermaid Syntax Expert Agent
mermaid_syntax_expert = Agent(
    role="Mermaid Syntax Expert",
    goal="Provide accurate and up-to-date information about Mermaid.js syntax, and validate and correct any generated Mermaid syntax.",
    backstory=(
        "You are an expert on Mermaid.js syntax. "
        "You have access to the latest Mermaid.js documentation and can provide "
        "clear and concise answers to syntax-related questions."
    ),
    llm=llm,
    tools=[scrape_tool, generate_mermaid_diagram_tool], # Added generate_mermaid_diagram_tool
    allow_delegation=False,
    verbose=True
)

def run_crew(query: str, tool_choice: str):
    """
    Runs the Crew to process a user query.

    Args:
        query: The user's query.

    Returns:
        The result of the crew execution.
    """
    # Define the tasks
    structuring_task = Task(
        description=f"Analyze the following user query and break it down into a list of simple, clear, and actionable steps. Query: {query}",
        agent=requirement_structuring_agent,
        expected_output="A numbered list of clear, step-by-step tasks for an RPA workflow."
    )

    mapping_task_description = f"""Take the structured list of tasks and create a flowchart structure in a JSON format using the '{tool_choice}' toolset.
        **IMPORTANT**: Use the `rpa_actions_search` tool to find relevant actions for the '{tool_choice}' toolset.
        The JSON should have 'nodes' and 'edges' keys.
        Each node should have an 'id', 'data' with a 'label' (which should be the exact action name), and a 'shape' ('rectangle' for actions, 'diamond' for decisions).
        Each edge should have an 'id', 'source', and 'target', and an optional 'label' for conditional branches ('True' or 'False')."""

    mapping_task = Task(
        description=mapping_task_description,
        agent=tool_mapper_agent,
        context=[structuring_task],
        expected_output="""A JSON object with 'nodes' and 'edges' that represents the workflow diagram.
    Example:
    {
        "nodes": [
            { "id": "1", "data": { "label": "Start" }, "shape": "rectangle" },
            { "id": "2", "data": { "label": "Check Condition" }, "shape": "diamond" }
        ],
        "edges": [
            { "id": "e1-2", "source": "1", "target": "2", "label": "" }
        ]
    }"""
    )

    mermaid_validation_task = Task(
        description="""Generate valid Mermaid.js syntax from the provided JSON object representing the workflow diagram. 
        The JSON object is available in the context from the `mapping_task` output. 
        Extract 'nodes' and 'edges' from the JSON and pass them as JSON strings to the `generate_mermaid_diagram_tool`. 
        Ensure the output is a valid Mermaid.js syntax string. If the generated syntax is not valid, try to correct it using your knowledge of Mermaid.js syntax and the `scrape_tool` if necessary.""", # Modified description

        agent=mermaid_syntax_expert,
        context=[mapping_task],
        expected_output="A valid Mermaid.js syntax string."
    )

    # Create a crew for the first two tasks
    crew = Crew(
        agents=[requirement_structuring_agent, tool_mapper_agent, mermaid_syntax_expert],
        tasks=[structuring_task, mapping_task, mermaid_validation_task],
        verbose=True
    )

    result = crew.kickoff()

    # Extract the outputs from the tasks
    structured_requirements = structuring_task.output.raw
    mapped_actions = ""
    flow_diagram_json_str = mapping_task.output.raw
    mermaid_syntax = mermaid_validation_task.output.raw

    try:
        if flow_diagram_json_str:
            flow_diagram_json = json.loads(flow_diagram_json_str)
            nodes = flow_diagram_json.get("nodes", [])
            edges = flow_diagram_json.get("edges", [])
        else:
            flow_diagram_json = {}
            nodes = []
            edges = []

    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Error processing flow diagram: {e}")
        flow_diagram_json = {}
        nodes = []
        edges = []

    return {
        "structured_requirements": structured_requirements,
        "flow_diagram_json": flow_diagram_json_str,
        "mermaid_syntax": mermaid_syntax,
    }