import streamlit as st
import requests
import json
from ui.ui import load_css, ui_topbar, ui_sidebar, ui_flow_tabs, landing_page

st.set_page_config(
    page_title="FlowPilot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
ui_topbar()
ui_sidebar()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show landing page if no messages
if not st.session_state.messages:
    landing_page()

# Place the tool selection dropdown
tool_options = ["-- Please select a tool --", "Power Automate", "Automation Anywhere"]
tool_choice_friendly = st.selectbox("Choose an RPA Tool", tool_options, key="tool_selection")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], dict):
            ui_flow_tabs(
                message["content"].get("mermaid_syntax"),
                message["content"].get("structured_requirements")
            )
        else:
            st.markdown(message["content"])

# Handle prompt from chat input
if prompt := st.chat_input("Describe what you’d like to automate…"):
    # Validate tool selection
    if tool_choice_friendly == "-- Please select a tool --":
        st.error("Please select an RPA tool from the dropdown before proceeding.")
        st.stop() # Stop execution to prevent further processing

    st.session_state.prompt = prompt

if "prompt" in st.session_state and st.session_state.prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": st.session_state.prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(st.session_state.prompt)

    # Display assistant response in chat message container
    with st.spinner("Thinking..."):
            try:
                # Map friendly name to collection name
                tool_choice_map = {
                    "Power Automate": "power_automate",
                    "Automation Anywhere": "automation_anywhere"
                }
                tool_choice = tool_choice_map[tool_choice_friendly]

                response = requests.get(f"http://127.0.0.1:8000/process-query?query={st.session_state.prompt}&tool_choice={tool_choice}")
                response.raise_for_status()
                results = response.json()

                st.session_state.messages.append({"role": "assistant", "content": results})

            except requests.exceptions.RequestException as e:
                st.error(f"Error connecting to the backend: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

    # Clear the prompt and rerun
    st.session_state.prompt = None
    st.rerun()