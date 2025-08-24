
from fastapi import FastAPI
from backend.services import search_rpa_actions
from backend.agents import run_crew
import os
import base64

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the FlowPilot API"}

@app.get("/search")
def search(query: str):
    """
    Searches for RPA actions based on a query.
    """
    return search_rpa_actions(query)

@app.get("/process-query")
def process_query(query: str, tool_choice: str = "power_automate"):
    """
    Processes the user's query using the CrewAI agents.
    """
    results = run_crew(query, tool_choice)

    return results


