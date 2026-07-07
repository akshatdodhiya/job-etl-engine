import streamlit as st
import os
from dotenv import load_dotenv, set_key
import database
from views import add_application, dashboard

# Load environment variables
load_dotenv()
# Save the .env inside the persistent, isolated Docker volume
ENV_PATH = "/app/data/.env" if os.path.exists("/app/data") else ".env"

# Ensure database exists on startup
database.init_db()

st.set_page_config(page_title="Job Application Tracker", page_icon="💼", layout="wide")

# Custom CSS for modern look & Navigation UI
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

    /* SIDEBAR NAVIGATION UPGRADE */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {
        background-color: transparent !important;
        border: none !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
        margin-bottom: 8px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background-color: rgba(76, 175, 80, 0.1) !important; 
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"],
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[aria-checked="true"] {
        background-color: #4CAF50 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label p {
        margin: 0 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[aria-checked="true"] p {
        color: white !important; 
    }
    </style>
""", unsafe_allow_html=True)

# Initialize ALL session state variables dynamically
session_states = {
    "extracted_data": None, "uploaded_resume_bytes": None, "uploaded_resume_name": None,
    "uploaded_posting_bytes": None, "uploaded_posting_name": None, "cover_letter_payload": None,
    "job_url": "", "uploader_key": 0, "save_success": False, "dashboard_key": 0, "dashboard_toast": None,
    "show_api_input": False # Controls the visibility of the API key input box
}
for key, default_value in session_states.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# ==========================================
# SIDEBAR CONFIGURATION & NAVIGATION
# ==========================================
with st.sidebar:
    st.title("🧭 Navigation")
    app_mode = st.radio("Navigation", ["➕ Add Application", "📊 Dashboard"], label_visibility="collapsed")
    
    st.divider()
    
    st.header("⚙️ Engine Selection")
    mock_mode = st.toggle("🛠️ Dev Mode (Mock API)", value=False, help="Use fake data to save API limits.")
    
    engine_choice = st.radio(
        "Processing Engine", 
        ["Gemini (Cloud)", "Ollama (Local)"],
        horizontal=True,
        label_visibility="collapsed"
    )

    current_api_key = os.environ.get("GEMINI_API_KEY", "")
    
    # Default fallback to False unless explicitly activated below
    fallback_enabled = False 

    if "Gemini" in engine_choice:
        st.subheader("🔑 Authentication")
        
        fallback_enabled = st.checkbox(
            "🔄 Auto-fallback to Local LLM", 
            value=True, 
            help="If Gemini hits a rate limit or network error, automatically process using Ollama."
        )
        
        if current_api_key and not st.session_state.show_api_input:
            st.success("✅ API Key Configured")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Update", use_container_width=True):
                    st.session_state.show_api_input = True
                    st.rerun()
            with col2:
                if st.button("🗑️ Remove", use_container_width=True):
                    if not os.path.exists(ENV_PATH): open(ENV_PATH, 'w').close()
                    set_key(ENV_PATH, "GEMINI_API_KEY", "")
                    os.environ["GEMINI_API_KEY"] = ""
                    st.rerun()
        else:
            new_key = st.text_input("Enter Gemini API Key", type="password")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save", use_container_width=True):
                    if new_key:
                        if not os.path.exists(ENV_PATH): open(ENV_PATH, 'w').close()
                        set_key(ENV_PATH, "GEMINI_API_KEY", new_key)
                        os.environ["GEMINI_API_KEY"] = new_key
                        st.session_state.show_api_input = False
                        st.rerun()
                    else:
                        st.error("Key cannot be empty.")
            with col2:
                if current_api_key and st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_api_input = False
                    st.rerun()
    else:
        st.info("🧠 Running local model: **qwen2.5:7b**\n\n*Note: First run triggers an automatic download (~4.5GB).*")

    st.divider()
    
    with st.expander("⚙️ Advanced Settings", expanded=False):
        base_job_dir = st.text_input("Jobs Directory Base", value=r"/app/jobs", help="Base directory for storing job postings, resumes, and cover letters. Must be writable.")
        st.caption("Mapped to Docker volume.", help="⚠️ Do not modify unless you know what you're doing.")
        
        selected_models = st.multiselect(
            "Model Fallback List",
            options=['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash'],
            default=['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
        )

# ==========================================
# VIEW ROUTING
# ==========================================
if app_mode == "➕ Add Application":
    engine_str = "Gemini" if "Gemini" in engine_choice else "Ollama"
    # Pass the dynamically managed current_api_key down to the view
    add_application.render(mock_mode, current_api_key, base_job_dir, selected_models, engine_str, fallback_enabled)
elif app_mode == "📊 Dashboard":
    dashboard.render()