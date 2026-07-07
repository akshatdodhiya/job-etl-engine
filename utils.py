import os
import re
import io
import email
from email import policy
from datetime import datetime
from pypdf import PdfReader
from bs4 import BeautifulSoup
from google import genai
import ollama
from pydantic import BaseModel, Field

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
    key_requirements: str = Field(description="Extract a MAXIMUM of 5 technical skills or keywords. Format exactly as a comma-separated list (e.g., 'Python, SQL, Docker'). DO NOT write full sentences.")
    contact_recruiter: str = Field(description="Name of the human recruiter. Ignore web form artifacts like 'First Name * Last Name *'. If no specific human name is mentioned, strictly output 'n/a'.")
    priority: str = Field(description=f"Perceived priority based on requirements. Must be one of: {', '.join(PRIORITIES)}. Default to 'Medium'.")

def sanitize_filename(name: str, max_len: int = 40) -> str:
    """Removes invalid characters, Excel-breaking brackets, and truncates length."""
    clean = re.sub(r'[\\/*?:"<>|\[\]]', "", name).strip(" .")
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
            msg = email.message_from_bytes(file_bytes, policy=policy.default)
            html_content = ""
            for part in msg.walk():
                if part.get_content_type() in ['text/html', 'text/plain']:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            html_content += payload.decode(charset, errors='ignore') + " "
                        except LookupError:
                            html_content += payload.decode('utf-8', errors='ignore') + " "
                            
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
        try:
            return file_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Fallback extraction error: {e}")
            return ""

def _ensure_local_model(model_name: str):
    """Cold-start handler: checks if the model exists locally, pulls it if not."""
    try:
        existing_models = [m['name'] for m in ollama.list().get('models', [])]
        if not any(model_name in m for m in existing_models):
            print(f"Downloading {model_name} locally... This may take a few minutes.")
            ollama.pull(model_name)
    except Exception as e:
        print(f"Ollama connection/pull failed: {e}")

def extract_job_data(text: str, api_key: str, job_url: str = "", models: list = None, mock_mode: bool = False, engine: str = "Gemini", fallback_to_local: bool = True, local_model: str = "qwen2.5:7b") -> JobExtraction:
    """Extracts job data with unified routing between Gemini API and Local Ollama."""
    
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
    
    text = text[:150000] 
    
    prompt = f"""
    You are an expert technical recruiter AI. Extract the requested job details from the raw text below.
    
    CRITICAL WARNING: The text is raw scraped HTML. You MUST IGNORE all website navigation menus, footer links, cookie policies, and generic web forms (e.g., "First Name *", "Last Name *", "Email *", "Submit Resume"). Focus ONLY on the actual job description content.

    STRICT FIELD RULES:
    1. 'key_requirements': You are forbidden from writing sentences. You MUST output a simple, comma-separated list of a MAXIMUM of 5 technical skills or keywords (e.g., "Python, Docker, AWS, React"). 
    2. 'contact_recruiter': ONLY output a specific human name if one is explicitly mentioned as the hiring manager or recruiter. If you see generic form fields or "First Name *", you MUST output "n/a".
    3. 'salary_range': If explicit salary numbers are not present, output strictly "n/a". Do not guess.

    Context Information:
    Job URL: {job_url if job_url else 'None provided'} (Use this to determine the 'platform').
    
    Raw Job Posting Text:
    {text}
    """
    
    last_error = None

    # 1. Cloud Execution (Gemini)
    if engine == "Gemini" and api_key:
        client = genai.Client(api_key=api_key)
        if not models:
            models = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
            
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
                print(f"Gemini {model_name} failed: {e}")
                last_error = e
                continue
                
        if not fallback_to_local:
            raise Exception(f"All Gemini models failed. Last error: {last_error}")
        else:
            print("Gemini API failed. Falling back to local LLM...")

    # 2. Local Execution (Ollama Fallback or Native)
    _ensure_local_model(local_model)
    
    try:
        response = ollama.chat(
            model=local_model,
            messages=[{'role': 'user', 'content': prompt}],
            # Force Ollama to strictly adhere to the Pydantic JSON schema
            format=JobExtraction.model_json_schema(),
            options={'temperature': 0.0}
        )
        return JobExtraction.model_validate_json(response['message']['content'])
    except Exception as e:
        raise Exception(f"Local LLM extraction failed. Last error: {e}")

def find_or_create_company_folder(base_dir: str, company_name: str, api_key: str, models: list = None, engine: str = "Gemini", fallback_to_local: bool = True, local_model: str = "qwen2.5:7b") -> str:
    """Finds an existing company folder using LLM-powered fuzzy matching with local fallback."""
    if not os.path.exists(base_dir):
        return os.path.join(base_dir, sanitize_filename(company_name))
        
    existing_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    
    if not existing_folders:
        return os.path.join(base_dir, sanitize_filename(company_name))
        
    prompt = f"""
    I am organizing job application folders. The new company I am applying to is "{company_name}".
    Here is a list of my existing company folders:
    {existing_folders}
    
    Does "{company_name}" refer to the exact same company as any of these existing folders? 
    Consider acronyms, common names, and subsidiaries (e.g., BMO = Bank of Montreal, Scotia = Scotiabank, TD = Toronto-Dominion).
    If YES, output ONLY the exact name of the existing folder from the list.
    If NO, output ONLY "NONE".
    """

    match = None

    # Try Gemini First
    if engine == "Gemini" and api_key:
        client = genai.Client(api_key=api_key)
        if not models:
            models = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
            
        for model_name in models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={'temperature': 0.0}
                )
                match_text = response.text.strip()
                if match_text in existing_folders:
                    return os.path.join(base_dir, match_text)
                match = match_text
                break 
            except Exception as e:
                print(f"Gemini {model_name} failed for folder matching: {e}")
                continue
                
    # Fallback to Local LLM
    if (not match or engine == "Ollama") and fallback_to_local:
        _ensure_local_model(local_model)
        try:
            response = ollama.chat(
                model=local_model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0}
            )
            match_text = response['message']['content'].strip()
            if match_text in existing_folders:
                return os.path.join(base_dir, match_text)
        except Exception as e:
            print(f"Local LLM failed for folder matching: {e}")
        
    # Standard string matching as final fallback
    company_lower = company_name.lower()
    for folder in existing_folders:
        folder_lower = folder.lower()
        if (folder_lower in company_lower and len(folder_lower) > 2) or (company_lower in folder_lower and len(company_lower) > 2):
            return os.path.join(base_dir, folder)
            
    return os.path.join(base_dir, sanitize_filename(company_name))