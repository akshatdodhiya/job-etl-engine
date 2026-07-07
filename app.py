import streamlit as st
import os
from dotenv import load_dotenv, set_key
import database
from views import add_application, dashboard

# Load environment variables
load_dotenv()
ENV_PATH = ".env"

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
    "show_api_input": False # NEW: Controls the visibility of the API key input box
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
    
    # --- SECURE AUTHENTICATION MODULE ---
    st.header("🔑 Authentication")
    mock_mode = st.toggle("🛠️ Dev Mode (Mock API)", value=True, help="Enable to use fake data and save your API quota.")
    
    # Grab current key directly from the environment
    current_api_key = os.environ.get("GEMINI_API_KEY", "")

    if mock_mode:
        st.info("Dev Mode is active. API calls are bypassed.")
    else:
        # State 1: Key is configured and the user hasn't asked to edit it
        if current_api_key and not st.session_state.show_api_input:
            st.success("✅ API Key Configured")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Update", use_container_width=True):
                    st.session_state.show_api_input = True
                    st.rerun()
            with col2:
                if st.button("🗑️ Remove", use_container_width=True):
                    # Nuke the key from both the live environment and the .env file
                    if not os.path.exists(ENV_PATH): open(ENV_PATH, 'w').close()
                    set_key(ENV_PATH, "GEMINI_API_KEY", "")
                    os.environ["GEMINI_API_KEY"] = ""
                    st.rerun()
                    
        # State 2: Key is missing OR user clicked "Update"
        else:
            new_key = st.text_input("Enter Gemini API Key", type="password", help="Get your free key from Google AI Studio.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save", use_container_width=True):
                    if new_key:
                        # Write the new key to the .env file for persistence
                        if not os.path.exists(ENV_PATH): open(ENV_PATH, 'w').close()
                        set_key(ENV_PATH, "GEMINI_API_KEY", new_key)
                        os.environ["GEMINI_API_KEY"] = new_key
                        st.session_state.show_api_input = False
                        st.rerun()
                    else:
                        st.error("Key cannot be empty.")
            with col2:
                # Only show cancel if they already have a key and are just updating
                if current_api_key and st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_api_input = False
                    st.rerun()

    st.divider()
    
    with st.expander("⚙️ Advanced Settings", expanded=False):
        base_job_dir = st.text_input("Jobs Directory Base", value=r"e:\Jobs\SDE")
        st.caption("⚠️ Docker: change to mounted Linux path (e.g., /app/jobs).")
        
        selected_models = st.multiselect(
            "Model Fallback List",
            options=['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash'],
            default=['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
        )

# ==========================================
# VIEW ROUTING
# ==========================================
if app_mode == "➕ Add Application":
    # Pass the dynamically managed current_api_key down to the view
    add_application.render(mock_mode, current_api_key, base_job_dir, selected_models)
elif app_mode == "📊 Dashboard":
    dashboard.render()