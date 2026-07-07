import os
import re
import io
import email
from email import policy
from datetime import datetime
from pypdf import PdfReader
from bs4 import BeautifulSoup
from google import genai
from pydantic import BaseModel, Field

# User's Excel dropdown options
PLATFORMS = ["LinkedIn", "Indeed", "Glassdoor", "Company Website", "Workday Portal", "Greenhouse", "AngelList / Wellfound", "Referral", "Job Fair", "Recruiter (Outbound)", "Other"]
JOB_TYPES = ["Full-Time", "Part-Time", "Contract", "Contract-to-Hire", "Co-op / Internship", "Freelance"]
COVER_LETTERS = ["Yes", "No", "Tailored Letter", "Generic Letter"]
STATUSES = ["Applied", "Phone Screen", "Interview Scheduled", "Technical Test", "Final Round", "Offer Received", "Accepted", "Rejected", "Withdrawn", "Ghosted"]
PRIORITIES = ["High", "Medium", "Low"]

class JobExtraction(BaseModel):
    company: str = Field(description="The name of the company hiring.")
    role_title: str = Field(description="The job title or role.")
    location: str = Field(description="The location of the job (e.g. city, province/state/country). If it is a remote job, output 'Remote'. If not explicitly mentioned, output an empty string ''")
    job_type: str = Field(description=f"The type of job. Must be one of: {', '.join(JOB_TYPES)}. Default to 'Full-Time' if unsure.")
    platform: str = Field(description=f"The platform the job is posted on. Must be one of: {', '.join(PLATFORMS)}. Default to 'Company Website' if unsure.")
    salary_range: str = Field(description="The salary range mentioned. If not explicitly mentioned anywhere, output strictly 'n/a'.")
    key_requirements: str = Field(description="Analyze the posting and extract the top 4-5 most important keywords or skills. Output ONLY those 4-5 words as a comma-separated list. No bullet points or sentences.")
    contact_recruiter: str = Field(description="Name or contact info of the recruiter if mentioned, otherwise 'n/a'.")
    priority: str = Field(description=f"Perceived priority based on requirements. Must be one of: {', '.join(PRIORITIES)}. Default to 'Medium'.")

def sanitize_filename(name: str, max_len: int = 40) -> str:
    """Removes invalid characters, Excel-breaking brackets, and truncates length."""
    # Strip illegal path chars AND square brackets (Excel hates brackets in links)
    clean = re.sub(r'[\\/*?:"<>|\[\]]', "", name).strip(" .")
    
    # Truncate to prevent 255-char Excel path limits
    # We strip again at the end just in case the truncation leaves a trailing space
    return clean[:max_len].strip(" .")

def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> str:
    """Extracts raw text from PDF, HTML, or MHTML bytes."""
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == '.pdf':
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return ""
            
    elif ext in ['.mhtml', '.mht']:
        try:
            # Parse the MHTML file as a MIME email message
            msg = email.message_from_bytes(file_bytes, policy=policy.default)
            html_content = ""
            
            # Walk through the multi-part structure
            for part in msg.walk():
                # Target only the actual text or HTML payloads, ignoring images/css
                if part.get_content_type() in ['text/html', 'text/plain']:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            html_content += payload.decode(charset, errors='ignore') + " "
                        except LookupError:
                            html_content += payload.decode('utf-8', errors='ignore') + " "
                            
            # Pass the isolated HTML payload to BeautifulSoup for text extraction
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            print(f"MHTML extraction error: {e}")
            return ""
            
    elif ext in ['.html', '.htm']:
        try:
            soup = BeautifulSoup(file_bytes, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            print(f"HTML extraction error: {e}")
            return ""
            
    else:
        # Fallback for plain text or unknown
        try:
            return file_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Fallback extraction error: {e}")
            return ""

def extract_job_data_gemini(text: str, api_key: str, job_url: str = "", models: list = None, mock_mode: bool = False) -> JobExtraction:
    """Extracts job data using Gemini API via Structured Outputs with automatic model fallback."""

    # 🛑 MOCK BYPASS: Returns fake data instantly for UI testing
    if mock_mode:
        import time
        return JobExtraction(
            company="MockTech Industries",
            role_title="Senior Mock Developer",
            location="Remote",
            job_type="Full-Time",
            platform="LinkedIn" if "linkedin" in job_url.lower() else "Company Website",
            salary_range="$120,000 - $140,000",
            key_requirements="Python, Streamlit, Docker, SQLite, REST APIs",
            contact_recruiter="Jane Doe",
            priority="High"
        )
    
    client = genai.Client(api_key=api_key)
    
    if not models:
        models = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
        
    # Truncate text to fit within reasonable limits for Gemini context
    text = text[:150000] 
    
    prompt = f"""
    Analyze the following job posting text and extract the required fields.
    Pay close attention to the instructions for each field.
    If the Salary Range is not explicitly stated in the text, you MUST output 'n/a'. Do not guess or infer.
    
    Context Information:
    Job URL: {job_url if job_url else 'None provided'} (Use this to confidently determine the 'platform' field).
    
    Job Posting Text:
    {text}
    """
    
    last_error = None
    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': JobExtraction,
                    'temperature': 0.1,
                },
            )
            return JobExtraction.model_validate_json(response.text)
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            last_error = e
            continue
            
    raise Exception(f"All selected models failed. Last error: {last_error}")

def find_or_create_company_folder(base_dir: str, company_name: str, api_key: str, models: list = None) -> str:
    """
    Intelligently finds an existing company folder using LLM-powered fuzzy matching with model fallback.
    If 'Bank of Montreal' is passed and 'BMO' exists, it intelligently matches it.
    If nothing matches, it returns a new sanitized folder path.
    """
    if not os.path.exists(base_dir):
        return os.path.join(base_dir, sanitize_filename(company_name))
        
    existing_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    
    if not existing_folders:
        return os.path.join(base_dir, sanitize_filename(company_name))
        
    # Use Gemini to intelligently match acronyms/alternative names
    client = genai.Client(api_key=api_key)
    prompt = f"""
    I am organizing job application folders. The new company I am applying to is "{company_name}".
    Here is a list of my existing company folders:
    {existing_folders}
    
    Does "{company_name}" refer to the exact same company as any of these existing folders? 
    Consider acronyms, common names, and subsidiaries (e.g., BMO = Bank of Montreal, Scotia = Scotiabank, TD = Toronto-Dominion).
    If YES, output ONLY the exact name of the existing folder from the list.
    If NO, output ONLY "NONE".
    """
    
    if not models:
        models = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
        
    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={'temperature': 0.0}
            )
            match = response.text.strip()
            # Ensure the LLM didn't hallucinate a folder name
            if match in existing_folders:
                return os.path.join(base_dir, match)
            break # LLM succeeded but no match found, don't fallback to other models
        except Exception as e:
            print(f"Model {model_name} failed for folder matching: {e}")
            continue
        
    # Fallback to simple substring match if LLM fails
    company_lower = company_name.lower()
    for folder in existing_folders:
        folder_lower = folder.lower()
        if (folder_lower in company_lower and len(folder_lower) > 2) or (company_lower in folder_lower and len(company_lower) > 2):
            return os.path.join(base_dir, folder)
            
    # No match found, create new
    return os.path.join(base_dir, sanitize_filename(company_name))


