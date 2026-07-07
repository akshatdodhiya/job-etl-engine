import streamlit as st
from datetime import datetime
import utils
import database

def render():
    st.subheader("📊 Application Dashboard")
    st.markdown("View, edit, and manage your applications. **Click any column header to sort.**")
    
    if st.session_state.dashboard_toast:
        st.toast(st.session_state.dashboard_toast)
        st.session_state.dashboard_toast = None
    
    df = database.get_all_applications()
    
    if df.empty:
        st.info("No applications found. Head over to 'Add Application' to extract your first job posting!")
    else:
        total_apps = len(df)
        interviews = len(df[df['status'].isin(['Phone Screen', 'Interview Scheduled', 'Technical Test', 'Final Round'])])
        offers = len(df[df['status'].isin(['Offer Received', 'Accepted'])])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Applications", total_apps)
        m2.metric("Active Interviews", interviews)
        m3.metric("Offers", offers)
        
        with m4:
            st.write("") 
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export CSV",
                data=csv,
                file_name=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                width="stretch"
            )
            
        st.write("") 
        
        df["Select"] = False
        current_editor_key = f"db_editor_{st.session_state.dashboard_key}"
        
        edited_df = st.data_editor(
            df,
            key=current_editor_key,
            width="stretch",
            height=600,         
            hide_index=False,
            column_order=[
                "Select", "company", "role_title", "status", "priority", 
                "salary_range", "location", "job_type", "platform", "job_url", 
                "contact_recruiter", "cover_letter", "key_requirements", "notes",
                "posting_path", "resume_path", "date_applied", "last_updated"
            ],
            column_config={
                "id": None,     
                "company": "Company",
                "role_title": "Role / Title",
                "location": "Location",
                "job_type": st.column_config.SelectboxColumn("Job Type", options=utils.JOB_TYPES),
                "platform": st.column_config.SelectboxColumn("Platform", options=utils.PLATFORMS),
                "job_url": st.column_config.LinkColumn("Job URL"),
                "posting_path": "Posting Path",
                "resume_path": "Resume Path",
                "cover_letter": "Cover Letter Path", 
                "contact_recruiter": "Recruiter",
                "status": st.column_config.SelectboxColumn("Status", options=utils.STATUSES),
                "priority": st.column_config.SelectboxColumn("Priority", options=utils.PRIORITIES),
                "salary_range": "Salary Range",
                "key_requirements": "Key Requirements",
                "notes": "Notes",
                "date_applied": st.column_config.TextColumn("Date Applied", disabled=True),
                "last_updated": st.column_config.TextColumn("Last Updated", disabled=True),
                "Select": st.column_config.CheckboxColumn("☑️", default=False, width="small")
            }
        )

        selected_rows = edited_df[edited_df["Select"] == True]
        if not selected_rows.empty:
            st.markdown("---")
            st.error(f"⚠️ You have selected {len(selected_rows)} application(s) for deletion.")
            if st.button("🗑️ Permanently Delete Selected", type="primary"):
                for idx, row in selected_rows.iterrows():
                    database.delete_application(row["id"])
                st.session_state.dashboard_key += 1
                st.rerun()

        if current_editor_key in st.session_state:
            state = st.session_state[current_editor_key]
            
            if state.get("edited_rows"):
                db_updated = False
                needs_revert = False
                
                for row_idx_str, updates in state["edited_rows"].items():
                    row_idx = int(row_idx_str)
                    
                    if row_idx >= len(df): continue
                        
                    app_id = int(df.iloc[row_idx]["id"])
                    
                    if "Select" in updates:
                        del updates["Select"]
                        
                    invalid_edit = False
                    for req_col in ["company", "role_title"]:
                        if req_col in updates and (updates[req_col] is None or str(updates[req_col]).strip() == ""):
                            st.session_state.dashboard_toast = f"⚠️ '{req_col.title().replace('_', ' ')}' cannot be blank. Change reverted."
                            invalid_edit = True
                            needs_revert = True
                            
                    if invalid_edit: continue 
                        
                    if updates:
                        try:
                            database.update_application(app_id, updates)
                            db_updated = True
                        except Exception as e:
                            st.session_state.dashboard_toast = f"❌ Update failed: {e}"
                            needs_revert = True
                            
                if needs_revert:
                    st.session_state.dashboard_key += 1
                    st.rerun()
                elif db_updated:
                    st.rerun()