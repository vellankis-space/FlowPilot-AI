import streamlit as st
import json

def load_css():
    with open("/Users/apple/Desktop/FlowPilot-AI/frontend/ui/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def ui_topbar():
    st.markdown(f"""
        <div class="app-bar">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 24px; margin-right: 10px;">🚀</span>
                <h2 style="color: var(--text);">FlowPilot</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)

def ui_sidebar():
    with st.sidebar:
        st.header("Recent Runs")
        st.text("No recent runs yet.")

        st.header("Settings")
        st.text_input("API Key", type="password", placeholder="Enter your API key")


def ui_flow_tabs(mermaid_syntax, steps):
    tab1, tab2 = st.tabs(["Flowchart", "Steps"])
    with tab1:
        if mermaid_syntax:
            html_mermaid = f"""
            <div class="mermaid" style="height: 500px;">
                {mermaid_syntax}
            </div>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <script>
                var mermaidConfig = {{
                    startOnLoad: true,
                    theme: 'dark',
                    flowchart: {{
                        nodeSpacing: 80,
                        rankSpacing: 80
                    }},
                    themeVariables: {{
                        fontSize: '14px'
                    }}
                }};
                mermaid.initialize(mermaidConfig);
            </script>
            """
            st.components.v1.html(html_mermaid, height=500, scrolling=True)
        else:
            st.warning("No flowchart to display.")
    with tab2:
        st.markdown(steps)

def landing_page():
    st.subheader("AI-Powered RPA Flow Designer: From plain English to automated workflow.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("##### 💡 Turn requirements → flows")
    with col2:
        st.markdown("##### 📋 Step-by-step build plan")
    with col3:
        st.markdown("##### 🚀 Deploy & export")
