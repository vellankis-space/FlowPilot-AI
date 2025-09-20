# FlowPilot-AI 🚀

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-green.svg)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-yellow.svg)](https://fastapi.tiangolo.com/)
[![CrewAI](https://img.shields.io/badge/CrewAI-Agents-orange.svg)](https://www.crewai.io/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5-blueviolet.svg)](https://openai.com/)

FlowPilot-AI is an intelligent RPA (Robotic Process Automation) workflow designer that transforms natural language descriptions into visual flowcharts. Using advanced AI agents, it analyzes user requirements, maps them to specific RPA actions, and generates executable flow diagrams in Mermaid.js syntax.

## 🌟 Features

- **Natural Language Processing**: Describe your automation needs in plain English
- **Multi-Platform RPA Support**: Works with Power Automate and Automation Anywhere
- **AI-Powered Agents**: Specialized agents for requirement structuring, tool mapping, and diagram generation
- **Visual Workflow Generation**: Creates interactive flowcharts using Mermaid.js
- **Vector Database Integration**: Semantic search through RPA action libraries
- **Modern UI**: Streamlit-based interface with dark/light theme support
- **Containerized Deployment**: Docker support for easy deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│   Streamlit     │    │      FastAPI         │    │    AI Agents         │
│   Frontend      │◄──►│      Backend         │◄──►│   (CrewAI)           │
└─────────────────┘    └──────────────────────┘    └──────────────────────┘
                              │                           │
                              ▼                           ▼
                    ┌──────────────────────┐    ┌──────────────────────┐
                    │   Vector Database    │    │   RPA Action Docs    │
                    │     (ChromaDB)       │    │    (Web Scraped)     │
                    └──────────────────────┘    └──────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Graphviz (for diagram generation)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/FlowPilot-AI.git
   cd FlowPilot-AI
   ```

2. **Install system dependencies:**
   
   **macOS:**
   ```bash
   brew install graphviz
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install graphviz graphviz-dev
   ```

3. **Set up Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Run the application:**
   ```bash
   # Start the backend server
   uvicorn backend.main:app --reload
   
   # In a new terminal, start the frontend
   streamlit run frontend/app.py
   ```

### Docker Deployment

```bash
# Build the Docker image
docker build -t flowpilot-ai .

# Run the container
docker run -p 8000:8000 -p 8501:8501 flowpilot-ai
```

## 🧠 How It Works

1. **Requirement Analysis**: The Requirement Analyst agent breaks down your natural language query into structured steps
2. **Tool Mapping**: The Tool Mapper agent matches these steps to specific RPA actions using semantic search
3. **Diagram Generation**: The Mermaid Expert agent creates a visual workflow diagram
4. **Visualization**: The frontend displays the generated flowchart in an interactive interface

## 📁 Project Structure

```
FlowPilot-AI/
├── backend/                 # FastAPI backend services
│   ├── agents.py           # CrewAI agents implementation
│   ├── diagram_generator.py # Mermaid diagram generation
│   ├── services.py         # Core backend services
│   ├── data/               # Scraped RPA documentation
│   └── vector_store/       # ChromaDB vector database
├── frontend/               # Streamlit frontend
│   ├── app.py              # Main Streamlit application
│   ├── ui/                 # UI components
│   └── assets/             # Static assets
├── .streamlit/             # Streamlit configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── README.md              # This file
```

## 🛠️ Technologies Used

- **Frontend**: [Streamlit](https://streamlit.io/) - For creating the web interface
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance API framework
- **AI Agents**: [CrewAI](https://www.crewai.io/) - Framework for orchestrating AI agents
- **Vector Database**: [ChromaDB](https://www.trychroma.com/) - For semantic search capabilities
- **Diagram Generation**: [Mermaid.js](https://mermaid-js.github.io/) - For visualizing workflows
- **RPA Integration**: Power Automate & Automation Anywhere connectors
- **Containerization**: [Docker](https://www.docker.com/) - For deployment consistency

## 📚 Documentation

### API Endpoints

- `GET /` - Health check endpoint
- `GET /search?query={query}` - Search RPA actions
- `GET /process-query?query={query}&tool_choice={tool}` - Process natural language query

### Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key for GPT-5 access

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [CrewAI](https://www.crewai.io/) for the multi-agent framework
- [Microsoft Power Automate](https://flow.microsoft.com/) and [Automation Anywhere](https://www.automationanywhere.com/) for their documentation
- [Mermaid.js](https://mermaid-js.github.io/) for diagram visualization
- [OpenAI](https://openai.com/) for the GPT models

## 📞 Support

For support, please open an issue on the GitHub repository or contact the maintainers.