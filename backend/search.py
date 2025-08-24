import sys
from dotenv import load_dotenv
from backend.services import search_rpa_actions # Import the function

load_dotenv()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        search_query = sys.argv[1]
        search_results = search_rpa_actions(search_query)
        print("\n--- Search Results ---")
        print(search_results)
    else:
        print("Please provide a search query as a command-line argument.")
")