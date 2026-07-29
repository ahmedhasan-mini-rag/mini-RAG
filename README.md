# mini-RAG

**mini-RAG** is a lightweight, modular backend API for Retrieval-Augmented Generation (RAG), built with FastAPI. It enables you to easily ingest documents, generate and store vector embeddings, and perform semantic search and question answering using state-of-the-art LLMs. 

## Features

- **FastAPI-powered**: High-performance, asynchronous REST API.
- **Multi-Provider LLM Support**: Seamlessly integrate with OpenAI, Cohere, and Google for chat and embeddings.
- **Document Processing**: Upload and chunk text and PDF documents effortlessly.
- **Vector Database Integration**: Store and query embeddings using providers like Qdrant.
- **Metadata Management**: MongoDB integration to keep track of projects, assets, and document chunks.
- **Robust Error Handling & Logging**: Centralized custom exceptions and FastAPI exception handlers, paired with structured YAML-based logging to catch and process errors gracefully while ensuring stable API responses.

## Requirements

- Python >= 3.12 
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (An extremely fast Python package and project manager)
- [Docker](https://docs.docker.com/engine/install/) (for running the MongoDB database)

## Setup Steps

1) **Clone the repository:**
    ```bash
    git clone https://github.com/AhmeDHasan-110/mini-RAG.git
    cd mini-RAG
    ```

2) **Setup a new environment using `uv`:**
    ```bash
    # Make sure you are in the root mini-RAG directory
    uv sync
    source .venv/bin/activate
    ```
    The `uv sync` command mainly does the following:
    - Creates a new virtual environment.
    - Installs all dependencies listed in `pyproject.toml`.
    - Installs the needed Python version if not found.

    > **Note**: After activating the environment, make sure your IDE (e.g., VS Code) uses this environment's Python interpreter. In VS Code, use `Ctrl+Shift+P` -> *Python: Select Interpreter*.
    
3) **Configure Environment Variables:**
    ```bash
    cp .env.example .env
    ```
    Open the newly created `.env` file and fill in your API keys (e.g., OpenAI, Cohere, Google) and preferred configuration values.

4) **Run MongoDB Server via Docker:**
    Navigate to the `docker` directory, configure its `.env` file, and start the service:
    ```bash
    cd docker
    cp .env.example .env
    # Edit docker/.env and add your credentials:
    # e.g., MONGO_ROOT_USERNAME=my_user, MONGO_ROOT_PASSWORD=user_pass
    
    sudo docker compose up -d
    cd ..
    ```

5) **Run the FastAPI Server:**
    Navigate to the `src` directory and start the `uvicorn` development server:
    ```bash
    cd src
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

## Usage & API Endpoints

Once the application is running, the easiest and most interactive way to explore and test the endpoints is through FastAPI's built-in **Swagger UI**. 

Navigate to **http://localhost:8000/docs** in your browser. From there, you can see all available endpoints, their expected JSON payloads, and you can send requests directly (just like Postman) without needing any external tools!

### Typical RAG Workflow

Here is a typical flow using the API (you can perform these sequentially via the `/docs` UI):

1. **Upload Documents (`POST /api/v1/data/upload/{project_name}`)**
   Upload your text or PDF files to a specific project workspace.

2. **Process & Chunk Files (`POST /api/v1/data/process/{project_name}`)**
   Process the uploaded files into smaller text chunks suitable for embedding.

3. **Generate Embeddings (`POST /api/v1/nlp/embed/{project_name}`)**
   Generate vector embeddings for the chunks using your configured LLM and store them in the Vector DB.

4. **Ask Questions (`POST /api/v1/nlp/answer/{project_name}`)**
   Send a query to retrieve relevant contexts from your documents and generate an AI-powered answer.

*Tip: If you prefer using Postman over the built-in Swagger UI, you could find a postman collection for the API's at `postman/` directory.*
