import streamlit as st
import os
from datetime import datetime
import utils
import database

def render(mock_mode, api_key, base_job_dir, selected_models, engine_str, fallback_enabled):
    st.title("⚙️ Job-ETL Engine")
    st.markdown("Automated ingestion, AI-driven transformation, and local database loading for unstructured job postings.")
    
    if st.session_state.save_success:
        st.success("Successfully saved to database!")
        st.balloons()
        st.session_state.save_success = False

    container1 = st.container(border=True)
    with container1:
        st.subheader("1. Extract Job Details")

        job_url_input = st.text_input(
            "Job Posting URL", 
            value=st.session_state.job_url,
            placeholder="https://www.linkedin.com/jobs/view/...",
            key=f"job_url_input_{st.session_state.uploader_key}"
        )

        st.write("") 
        
        cl_mode = st.radio(
            "Cover Letter Format", 
            ["📁 Upload File", "✍️ Paste Text"], 
            horizontal=True,
            key=f"cl_mode_{st.session_state.uploader_key}"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            posting_file = st.file_uploader(
                "Upload Job Posting *", 
                type=["pdf", "html", "htm", "mhtml", "mht"],
                key=f"posting_{st.session_state.uploader_key}"
            )
        with col2:
            resume_file = st.file_uploader(
                "Upload Resume (Optional)", 
                type=["pdf", "docx"],
                key=f"resume_{st.session_state.uploader_key}"
            )
        with col3:
            cl_file = None
            cl_text = ""
            if "Upload" in cl_mode:
                cl_file = st.file_uploader(
                    "Upload Cover Letter (Optional)", 
                    type=["pdf", "docx", "txt", "png", "jpg"], 
                    key=f"cl_file_{st.session_state.uploader_key}"
                )
            else:
                cl_text = st.text_area(
                    "Paste Cover Letter (Optional)", 
                    height=110, 
                    placeholder="Dear Hiring Manager...", 
                    key=f"cl_text_{st.session_state.uploader_key}"
                )

        st.write("") 
        extract_btn = st.button("🚀 Extract Data", width="stretch")

    if extract_btn:
        if not mock_mode and engine_str == "Gemini" and not api_key:
            st.error("Please provide a Gemini API Key, or switch to the Local Ollama engine.")
        elif not posting_file:
            st.warning("Please upload the Job Posting file to extract data from.")
        else:
            st.session_state.job_url = job_url_input
            
            if resume_file:
                st.session_state.uploaded_resume_bytes = resume_file.getvalue()
                ext_res = os.path.splitext(resume_file.name)[1]
                st.session_state.uploaded_resume_name = f"Resume{ext_res}"
                
            st.session_state.uploaded_posting_bytes = posting_file.getvalue()
            ext_post = os.path.splitext(posting_file.name)[1]
            st.session_state.uploaded_posting_name = f"Listing{ext_post}"
            
            if "Upload" in cl_mode and cl_file:
                cl_ext = os.path.splitext(cl_file.name)[1]
                st.session_state.cover_letter_payload = (cl_file.getvalue(), f"CoverLetter{cl_ext}")
            elif "Paste" in cl_mode and cl_text.strip():
                st.session_state.cover_letter_payload = (cl_text.encode('utf-8'), "CoverLetter.txt")
            else:
                st.session_state.cover_letter_payload = None
            
            with st.spinner("Extracting text from uploaded file..."):
                page_text = utils.extract_text_from_file_bytes(st.session_state.uploaded_posting_bytes, posting_file.name)
                if not page_text:
                    st.error("Could not extract any text from the provided file.")
                    st.stop()
                    
            with st.spinner(f"Analyzing text with {engine_str}..."):
                try:
                    # Pass the explicit fallback flag to your backend utility
                    extracted = utils.extract_job_data(
                        text=page_text, 
                        api_key=api_key, 
                        job_url=st.session_state.job_url,
                        models=selected_models, 
                        mock_mode=mock_mode,
                        engine=engine_str,
                        fallback_to_local=fallback_enabled
                    )
                    st.session_state.extracted_data = extracted.model_dump()
                    st.success("Extraction successful! Please review the data below.")
                except Exception as e:
                    st.error(f"AI Extraction failed: {e}")
                    
    if st.session_state.extracted_data:
        review_container = st.empty()
        
        with review_container.container(border=True):
            st.subheader("2. Review & Save Application")
        
            with st.form("review_form"):
                st.markdown("Edit any fields before saving to the database.")
                
                c1, c2, c3 = st.columns(3)
                with c1: company = st.text_input("Company", value=st.session_state.extracted_data.get('company', ''), key="frm_company")
                with c2: role = st.text_input("Role / Title", value=st.session_state.extracted_data.get('role_title', ''), key="frm_role")
                with c3: salary = st.text_input("Salary Range", value=st.session_state.extracted_data.get('salary_range', 'n/a'), key="frm_salary")
                    
                c4, c5, c6, c7 = st.columns(4)
                with c4:
                    jtype_val = st.session_state.extracted_data.get('job_type', 'Full-Time')
                    jtype_idx = utils.JOB_TYPES.index(jtype_val) if jtype_val in utils.JOB_TYPES else 0
                    job_type = st.selectbox("Job Type", options=utils.JOB_TYPES, index=jtype_idx, key="frm_job_type")
                with c5:
                    plat_val = st.session_state.extracted_data.get('platform', 'Company Website')
                    plat_idx = utils.PLATFORMS.index(plat_val) if plat_val in utils.PLATFORMS else 0
                    platform = st.selectbox("Platform", options=utils.PLATFORMS, index=plat_idx, key="frm_platform")
                with c6:
                    status = st.selectbox("Status", options=utils.STATUSES, index=0, key="frm_status")
                with c7:
                    prio_val = st.session_state.extracted_data.get('priority', 'Medium')
                    prio_idx = utils.PRIORITIES.index(prio_val) if prio_val in utils.PRIORITIES else 1
                    priority = st.selectbox("Priority", options=utils.PRIORITIES, index=prio_idx, key="frm_priority")
                
                recruiter = st.text_input("Contact / Recruiter", value=st.session_state.extracted_data.get('contact_recruiter', 'n/a'), key="frm_recruiter")
                requirements = st.text_area("Key Requirements", value=st.session_state.extracted_data.get('key_requirements', ''), height=100, key="frm_requirements")
                loc = st.session_state.extracted_data.get('location', '')
                notes = st.text_area("Notes", value=f"Location: {loc}" if loc else "", key="frm_notes")
                
                submit = st.form_submit_button("💾 Save to Database", width="stretch")
                
        if submit:
            if not company or not role:
                st.error("Company and Role are required!")
            else:
                review_container.empty()
                
                with st.spinner("Saving files and generating DB record..."):
                    company_dir = utils.find_or_create_company_folder(
                        base_job_dir, company, api_key, 
                        models=selected_models, engine=engine_str
                    )
                    safe_role = utils.sanitize_filename(role)
                    target_dir = os.path.join(company_dir, safe_role)
                    
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
                    
                    final_posting_path = os.path.join(target_dir, f"{final_role_name}_{st.session_state.uploaded_posting_name}")
                    with open(final_posting_path, "wb") as f: f.write(st.session_state.uploaded_posting_bytes)
                        
                    final_resume_path = ""
                    if st.session_state.uploaded_resume_bytes:
                        final_resume_path = os.path.join(target_dir, st.session_state.uploaded_resume_name)
                        with open(final_resume_path, "wb") as f: f.write(st.session_state.uploaded_resume_bytes)
                            
                    final_cl_path = "No"
                    if st.session_state.cover_letter_payload:
                        cl_bytes, cl_name = st.session_state.cover_letter_payload
                        final_cl_path = os.path.join(target_dir, cl_name)
                        with open(final_cl_path, "wb") as f: f.write(cl_bytes)
                            
                    final_data = {
                        "company": company, "role_title": role, "location": loc, "job_type": job_type,
                        "platform": platform, "job_url": st.session_state.job_url,
                        "posting_path": final_posting_path, "resume_path": final_resume_path,
                        "cover_letter": final_cl_path, "contact_recruiter": recruiter,
                        "status": status, "priority": priority, "salary_range": salary,
                        "key_requirements": requirements, "notes": notes
                    }
                    
                    database.insert_application(final_data)
                    
                    st.session_state.extracted_data = None
                    st.session_state.uploaded_resume_bytes = None
                    st.session_state.uploaded_resume_name = None
                    st.session_state.uploaded_posting_bytes = None
                    st.session_state.uploaded_posting_name = None
                    st.session_state.cover_letter_payload = None
                    st.session_state.job_url = ""
                    st.session_state.uploader_key += 1
                    st.session_state.save_success = True
                    st.rerun()