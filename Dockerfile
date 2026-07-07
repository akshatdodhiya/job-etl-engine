# Use Astral's official, highly-optimized uv image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set the working directory
WORKDIR /app

# Install necessary system libraries for PDF and HTML parsing
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Tell uv to compile Python to bytecode to make Streamlit boot up faster
ENV UV_COMPILE_BYTECODE=1

# Step 1 of uv caching: Copy ONLY the configuration files first.
# This ensures Docker caches the heavy dependency installation step.
COPY pyproject.toml uv.lock ./

# Step 2: Install the dependencies inside the container using the lockfile.
# --frozen ensures uv strictly follows the uv.lock file and fails if it's out of sync.
# --no-install-project tells it to just grab the libraries, not the app code yet.
RUN uv sync --frozen --no-install-project

# Step 3: Now copy your actual application code (app.py, utils.py, views folder, etc.)
COPY . .

# Step 4: Sync the project code itself into the environment
RUN uv sync --frozen

# Expose Streamlit's default port
EXPOSE 8501

# Start the application using 'uv run' to ensure it executes inside the managed, locked environment
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]