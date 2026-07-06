from datetime import datetime
import streamlit as st
import os
from dotenv import load_dotenv
import utils

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Job Application Tracker Pro", page_icon="💼", layout="wide")

# Custom CSS for modern look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
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
    </style>
""", unsafe_allow_html=True)

st.title("💼 Job Application Tracker Pro")
st.markdown("Automate your job application tracking with AI-powered data extraction and manual file uploads.")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Google Gemini API Key", value=os.environ.get("GEMINI_API_KEY", ""), type="password")
    
    # Path configuration
    st.subheader("Paths")
    base_job_dir = st.text_input("Jobs Directory Base", value=r"e:\Jobs\SDE")
    st.caption("⚠️ Keep this path as short as possible (e.g., E:\\Jobs) to prevent Excel's 255-character hyperlink limit from breaking your links.")
    
    st.subheader("Models")
    selected_models = st.multiselect(
        "Model Fallback List (ordered by priority)",
        options=['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-3.5-pro', 'gemini-2.5-pro', 'gemini-1.5-pro'],
        default=['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
    )
    
    st.markdown("---")
    st.info("Make sure your API key is valid and the path matches your system.")

# Initialize session state variables
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "tsv_output" not in st.session_state:
    st.session_state.tsv_output = None
if "uploaded_resume_bytes" not in st.session_state:
    st.session_state.uploaded_resume_bytes = None
if "uploaded_resume_name" not in st.session_state:
    st.session_state.uploaded_resume_name = None
if "uploaded_posting_bytes" not in st.session_state:
    st.session_state.uploaded_posting_bytes = None
if "uploaded_posting_name" not in st.session_state:
    st.session_state.uploaded_posting_name = None
if "job_url" not in st.session_state:
    st.session_state.job_url = ""
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

container1 = st.container(border=True)
with container1:
    st.subheader("1. Extract Job Details")

    job_url_input = st.text_input("Job Posting URL (for hyperlinks)", placeholder="https://www.linkedin.com/jobs/view/...")

    col1, col2 = st.columns(2)
    with col1:
        posting_file = st.file_uploader("Upload Job Posting (PDF/HTML/MHTML)", 
                                        type=["pdf", "html", "htm", "mhtml", "mht"],
                                        key=f"posting_{st.session_state.uploader_key}")
    with col2:
        resume_file = st.file_uploader("Upload Used Resume (PDF/Docx)", 
                                       type=["pdf", "docx"],
                                       key=f"resume_{st.session_state.uploader_key}")

    extract_btn = st.button("🚀 Extract Data", use_container_width=True)

if extract_btn:
    if not api_key:
        st.error("Please provide a Gemini API Key in the sidebar.")
    elif not posting_file:
        st.warning("Please upload the Job Posting file to extract data from.")
    else:
        st.session_state.job_url = job_url_input
        
        # Save resume to session state only if provided
        if resume_file:
            st.session_state.uploaded_resume_bytes = resume_file.getvalue()
            ext_res = os.path.splitext(resume_file.name)[1]
            st.session_state.uploaded_resume_name = f"Resume{ext_res}"
        
        st.session_state.uploaded_posting_bytes = posting_file.getvalue()
        ext_post = os.path.splitext(posting_file.name)[1]
        st.session_state.uploaded_posting_name = f"Listing{ext_post}"
        
        with st.spinner("Extracting text from uploaded file..."):
            page_text = utils.extract_text_from_file_bytes(st.session_state.uploaded_posting_bytes, posting_file.name)
            if not page_text:
                st.error("Could not extract any text from the provided file.")
                st.stop()
                
        with st.spinner("Analyzing text with Gemini AI..."):
            try:
                extracted = utils.extract_job_data_gemini(
                    text=page_text, 
                    api_key=api_key, 
                    job_url=st.session_state.job_url,
                    models=selected_models
                )
                st.session_state.extracted_data = extracted.model_dump()
                st.session_state.tsv_output = None # Clear old TSV
                st.success("Extraction successful! Please review the data below.")
            except Exception as e:
                st.error(f"AI Extraction failed: {e}")
                
# Step 2: Review and Save
if st.session_state.extracted_data:
    container2 = st.container(border=True)
    with container2:
        st.subheader("2. Review & Save Files")
    
        with st.form("review_form"):
            st.markdown("Edit any fields before generating the Excel row.")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                company = st.text_input("Company", value=st.session_state.extracted_data.get('company', ''))
            with c2:
                role = st.text_input("Role / Title", value=st.session_state.extracted_data.get('role_title', ''))
            with c3:
                salary = st.text_input("Salary Range", value=st.session_state.extracted_data.get('salary_range', 'n/a'))
                
            c4, c5, c6, c7 = st.columns(4)
            with c4:
                jtype_val = st.session_state.extracted_data.get('job_type', 'Full-Time')
                jtype_idx = utils.JOB_TYPES.index(jtype_val) if jtype_val in utils.JOB_TYPES else 0
                job_type = st.selectbox("Job Type", options=utils.JOB_TYPES, index=jtype_idx)
            with c5:
                plat_val = st.session_state.extracted_data.get('platform', 'Company Website')
                plat_idx = utils.PLATFORMS.index(plat_val) if plat_val in utils.PLATFORMS else 0
                platform = st.selectbox("Platform", options=utils.PLATFORMS, index=plat_idx)
            with c6:
                status = st.selectbox("Status", options=utils.STATUSES, index=0)
            with c7:
                prio_val = st.session_state.extracted_data.get('priority', 'Medium')
                prio_idx = utils.PRIORITIES.index(prio_val) if prio_val in utils.PRIORITIES else 1
                priority = st.selectbox("Priority", options=utils.PRIORITIES, index=prio_idx)
                
            c8, c9 = st.columns(2)
            with c8:
                recruiter = st.text_input("Contact / Recruiter", value=st.session_state.extracted_data.get('contact_recruiter', 'n/a'))
            with c9:
                cover_letter = st.selectbox("Cover Letter?", options=utils.COVER_LETTERS, index=1)
                
            requirements = st.text_area("Key Requirements", value=st.session_state.extracted_data.get('key_requirements', ''), height=150)
            loc = st.session_state.extracted_data.get('location', '')
            default_notes = f"Location: {loc}" if loc and loc.lower() != '' else ""
            notes = st.text_area("Notes", value=default_notes)
            
            submit = st.form_submit_button("💾 Save Files & Generate Excel Row", use_container_width=True)
            
            if submit:
                if not company or not role:
                    st.error("Company and Role are required!")
                else:
                    with st.spinner("Saving files and generating row..."):
                        # 1. Intelligently Find or Create Company Directory
                        company_dir = utils.find_or_create_company_folder(base_job_dir, company, api_key, models=selected_models)
                        
                        # 2. Create Role Directory
                        safe_role = utils.sanitize_filename(role)
                        target_dir = os.path.join(company_dir, safe_role)
                        
                        # Handle folder clash (same position at same company)
                        if os.path.exists(target_dir):
                            date_suffix = datetime.now().strftime("%Y-%m-%d")
                            base_target = f"{target_dir}_{date_suffix}"
                            target_dir = base_target
                            counter = 2
                            while os.path.exists(target_dir):
                                target_dir = f"{base_target} ({counter})"
                                counter += 1
                                
                        os.makedirs(target_dir, exist_ok=True)
                        final_role_name = os.path.basename(target_dir)
                        
                        # 3. Save Files
                        final_posting_path = os.path.join(target_dir, f"{final_role_name}_{st.session_state.uploaded_posting_name}")
                        with open(final_posting_path, "wb") as f:
                            f.write(st.session_state.uploaded_posting_bytes)
                            
                        # Save resume only if one was uploaded
                        if st.session_state.uploaded_resume_bytes:
                            final_resume_path = os.path.join(target_dir, st.session_state.uploaded_resume_name)
                            with open(final_resume_path, "wb") as f:
                                f.write(st.session_state.uploaded_resume_bytes)
                        else:
                            final_resume_path = ""
                            
                        # 4. Generate TSV Row
                        final_data = {
                            "company": company,
                            "role_title": role,
                            "job_type": job_type,
                            "platform": platform,
                            "salary_range": salary,
                            "key_requirements": requirements,
                            "contact_recruiter": recruiter,
                            "status": status,
                            "priority": priority,
                            "cover_letter": cover_letter,
                            "notes": notes
                        }
                        
                        tsv_row = utils.generate_tsv_row(
                            data=final_data,
                            url=st.session_state.job_url,
                            posting_path=final_posting_path,
                            resume_path=final_resume_path
                        )
                        
                        st.session_state.tsv_output = tsv_row
                        st.success(f"Files saved to {target_dir}!")
                        st.balloons()

# Step 3: Display Output
if st.session_state.tsv_output:
    container3 = st.container(border=True)
    with container3:
        st.subheader("3. Copy & Paste to Excel")
        st.markdown("Click the copy icon in the top right of the dark code block below, then paste directly into an empty row in your `Applications` tab in Excel.")
        
        st.info("💡 **Excel Styling Tip**: Excel might leave the pasted links as black text. To make them beautifully blue and underlined instantly, just highlight those columns in Excel, go to the **Home** tab -> **Cell Styles** -> and click **Hyperlink**!")
        
        st.code(st.session_state.tsv_output, language="text")
        
        if st.button("Start New Application", use_container_width=True):
            st.session_state.extracted_data = None
            st.session_state.tsv_output = None
            st.session_state.uploaded_resume_bytes = None
            st.session_state.uploaded_resume_name = None
            st.session_state.uploaded_posting_bytes = None
            st.session_state.uploaded_posting_name = None
            st.session_state.uploader_key += 1
            st.rerun()
