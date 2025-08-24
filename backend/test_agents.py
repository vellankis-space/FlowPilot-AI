
import sys
import os

# Add the project root to the sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from backend.agents import run_crew

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
        result = run_crew(query)
        print(result)
    else:
        print("Please provide a query as a command-line argument.")
