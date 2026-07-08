# Job-ETL Engine

An AI-powered, privacy-first local web application designed to automate the extraction, tracking, and management of job applications. It uses a dual-engine LLM architecture to parse raw job descriptions from PDFs and web pages directly into a structured SQLite database.

## Features

* **Dual-Engine AI Routing:** Seamlessly toggle between Google's Gemini API (Cloud) and Ollama (Local) for data extraction. 
* **Automatic Fallback:** If the cloud API hits a rate limit or network error, the system automatically routes the extraction task to the local LLM.
* **Local-First Privacy:** Runs a local `qwen2.5:7b` model via Ollama. Job descriptions, resumes, and cover letters never have to leave your machine.
* **Structured Output:** Enforces strict JSON schemas using Pydantic, ensuring the LLM outputs clean, database-ready fields and ignores web-scraping artifacts.
* **Automated File Management:** Automatically generates isolated folder structures for each company and role, saving copies of the job posting, your resume, and your cover letter.
* **GPU Accelerated:** Native support for NVIDIA GPU passthrough in Docker for rapid local inference.

## Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | Python-based UI framework for rapid dashboard deployment. |
| **Backend** | Python 3.11 | Core logic, routing, and file processing (PyPDF, BeautifulSoup4). |
| **Data Enforcement** | Pydantic | Enforces strict JSON formatting for LLM outputs. |
| **Cloud AI** | Google GenAI SDK | High-speed cloud inference via Gemini models. |
| **Local AI** | Ollama | Local inference engine running `qwen2.5:7b`. |
| **Database** | SQLite & Pandas | Lightweight, serverless relational database and data manipulation. |
| **Infrastructure**| Docker & `uv` | Containerized orchestration and lightning-fast dependency resolution. |

## Prerequisites

Ensure you have the following installed on your host machine:
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (WSL2 enabled if on Windows)
2. *Optional:* [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (To utilize a local GPU for Ollama)

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/akshatdodhiya/job-etl-engine.git
   cd job-etl-engine
   ```

2. **Start the containers:**
   ```bash
   docker compose up --build -d
   ```

3. **Access the Application:**
   Open your browser and navigate to: `http://localhost:8501`

*Note: On your first execution using the Local Engine, the system will autonomously download the `qwen2.5:7b` model (~4.5GB). This will take a few minutes depending on your network connection.*

## Usage Guide

### 1. Engine Configuration
Navigate to the sidebar to select your Processing Engine.
* **Gemini (Cloud):** Requires an API key. Entering a key securely saves it to the isolated Docker volume. You can toggle the "Auto-fallback" option to reroute to Ollama if the API fails.
* **Ollama (Local):** Runs entirely on your hardware. No API key required.

### 2. Adding an Application
1. Paste the URL of the job posting.
2. Upload the Job Posting file (PDF, HTML, or MHTML).
3. Optionally upload your Resume and Cover Letter.
4. Click **Extract Data**. The AI will parse the document and populate the review form.
5. Verify the extracted fields, make any necessary edits, and click **Save to Database**. The application will automatically create an organized folder structure for the files.

### 3. Dashboard Management
Navigate to the Dashboard tab to view your structured data. You can edit cells directly in the table to update interview statuses, add notes, or flag priorities. Click "Export CSV" to download a local copy of your data.

## Architecture & Volume Management

To ensure the host machine's environment and local files are never corrupted by the container, this project enforces strict volume isolation:

| Volume Mount | Purpose |
| :--- | :--- |
| `db_storage` | Isolates the `tracker.db` SQLite database and the runtime `.env` file containing the API key. |
| `jobs_storage` | Persistently stores the scraped job postings, resumes, and cover letters safely inside Docker. |
| `ollama_storage` | Prevents Ollama from redownloading the 4.5GB LLM weights every time the container restarts. |
| `/app/.venv` | An anonymous volume preventing the container's Linux binaries from overwriting host environments. |

## Author

**Akshat Dodhiya**
* Website: [akshat.codes](https://akshat.codes)

## License

This project is open-source and available under the MIT License.