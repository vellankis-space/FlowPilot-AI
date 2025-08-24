## Project Overview

This project, "FlowPilot-AI," is a web-based application that helps users design Robotic Process Automation (RPA) workflows. Users can describe their automation needs in plain English, and the application will generate a flowchart and a step-by-step plan for building the RPA bot.

The application is built with a Python backend and a Streamlit frontend. The backend uses FastAPI to provide an API, and the core logic is powered by the `crewai` library, which orchestrates two AI agents: a "Requirement Analyst" and a "Tool Mapper." These agents use a large language model (LLM) from OpenAI to understand the user's request and generate the workflow. A Chroma vector database is used to store and search for available RPA actions.

The frontend is a simple chat interface built with Streamlit. It allows the user to input their requirements and then displays the generated flowchart and step-by-step instructions.

## Building and Running

### Dependencies

This project uses `pygraphviz` to generate flowcharts. `pygraphviz` requires the `graphviz` library to be installed on your system.

**macOS:**

```bash
brew install graphviz
```

**Ubuntu/Debian:**

```bash
sudo apt-get install graphviz graphviz-dev
```

### Backend

To run the backend server:

1.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
2.  Set up your OpenAI API key in a `.env` file. You can copy the `.env.example` file:
    ```bash
    cp .env.example .env
    ```
    Then, edit the `.env` file to add your API key.
3.  Start the FastAPI server:
    ```bash
    uvicorn backend.main:app --reload
    ```

The backend will be running at `http://127.0.0.1:8000`.

### Frontend

To run the frontend application:

1.  Make sure the backend server is running.
2.  Run the Streamlit app:
    ```bash
    streamlit run frontend/app.py
    ```

The frontend will be accessible in your web browser, usually at `http://localhost:8501`.

## Development Conventions

The project is divided into a `frontend` and a `backend` directory.

*   The `backend` directory contains the FastAPI application, the `crewai` agents, and the vector database logic.
*   The `frontend` directory contains the Streamlit application and its UI components.

The core logic of the application is in the `backend/agents.py` file. This file defines the AI agents and their tasks. The `backend/main.py` file defines the API endpoints that the frontend calls.

The frontend code is in `frontend/app.py`. It uses a separate `ui` module for the UI components.

When making changes, it's important to maintain this separation of concerns. Backend logic should be kept in the `backend` directory, and frontend code should be in the `frontend` directory.
