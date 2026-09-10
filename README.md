# mini-RAG

**mini-RAG** is a lightweight, modular, and production-ready backend API for Retrieval-Augmented Generation (RAG), built with FastAPI. It enables you to ingest multi-format documents, process complex PDFs with dedicated text, image, and table extraction, generate and store vector embeddings, perform semantic search, and serve AI-driven question answering—backed by full-stack observability with Prometheus and Grafana.

---

## Features

- **FastAPI Core**: High-performance, asynchronous REST API with structured error handling and YAML-based logging.
- **Multi-Provider LLM & Embedding Support**: Integrations with OpenAI, Cohere, and Google Gemini for chat completion and embedding generation.
- **Modular Document Ingestion Engine**:
  - Dedicated file loaders for `.pdf`, `.docx`, `.html`, `.md`, and `.txt` files.
  - **Production-Grade PDF Pipeline**: Multi-channel extraction engine supporting text, images, and tables with Vision LLM (VLM) OCR capabilities.  
    *(Note: Currently, extracting images and tables into the database is exclusively supported for PDF documents).*
- **Dual Vector Database Support**:
  - **Qdrant**: High-performance dedicated vector search engine.
  - **PostgreSQL (`pgvector`)**: Integrated vector similarity search directly within PostgreSQL.
- **Relational Metadata Management**: **PostgreSQL** handles project workspaces, file assets, and document chunk tracking.
- **Full-Stack Observability & Metrics**:
  - Prometheus metrics instrumentation (`/metrics` endpoint via `prometheus-client`).
  - Pre-configured Grafana dashboards for monitoring application throughput, latencies, database health, and host system metrics.
  - Infrastructure metrics exporters: **Node-Exporter** and **Postgres-Exporter**.
- **Production Architecture**: Orchestrated via **Docker Compose** behind an **Nginx** reverse proxy.

---

## Ecosystem Services

The complete application stack runs as containerized services managed via Docker Compose:

| Service | Container / Port | Description |
| :--- | :--- | :--- |
| **FastAPI App** | `fastapi_app` (8797) | RAG Backend application server |
| **Nginx** | `nginx` (80) | Reverse proxy routing incoming HTTP requests |
| **PostgreSQL (`pgvector`)** | `pgvector` (5432) | Relational metadata store and vector database |
| **Qdrant** | `qdrant` (6333) | Vector similarity search engine |
| **Prometheus** | `prometheus` (9090) | Time-series metrics collection and scraping |
| **Grafana** | `grafana` (3000) | Metrics visualization & observability dashboards |
| **Node Exporter** | `node_exporter` (9100) | Host system hardware & OS metrics collector |
| **Postgres Exporter** | `postgres_exporter` (9187) | PostgreSQL engine performance metrics collector |

---

## Setup & Execution

### 1. Clone the Repository
```bash
git clone https://github.com/AhmeDHasan-110/mini-RAG.git
cd mini-RAG
```

### 2. Docker Deployment (Recommended)
The application and all supporting services are fully containerized. 

For step-by-step instructions on setting up environment files (`.env.app`, `.env.postgres`, etc.), starting services, managing Docker volumes, and importing Grafana dashboards, please head over to the **[Docker Documentation](file:///home/ahmed-hasan110/Desktop/code/Projects/mini-RAG/docker/README.md)**.

Quick launch summary:
```bash
cd docker
# Create environment files as described in docker/README.md, then run:
docker compose up --build -d
```

### 3. Local Development with `uv` (Optional)
If you prefer running the FastAPI application locally outside Docker:

1. **Install dependencies:**
   ```bash
   uv sync
   source .venv/bin/activate
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and DB credentials
   ```

3. **Start the Uvicorn server:**
   ```bash
   cd src
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Usage & API Workflows

### Testing via Postman
A ready-to-use Postman Collection is provided in the repository to let you inspect, configure, and execute all API endpoints immediately:
- **Collection Path**: [`postman/mini-rag-v1.0.0-api.postman_collection.json`](file:///home/ahmed-hasan110/Desktop/code/Projects/mini-RAG/postman/mini-rag-v1.0.0-api.postman_collection.json)

---

### Typical RAG Workflow & cURL Examples

#### Step 1: Upload Documents (`POST /api/data/upload/{project_name}`)
Upload supported documents (`.pdf`, `.docx`, `.html`, `.md`, `.txt`) into a named project workspace.

```bash
curl -X POST "http://localhost/api/data/upload/my_project" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@/path/to/sample_document.pdf"
```

#### Step 2: Process & Chunk Files (`POST /api/data/process/{project_name}`)
Parse asset content into chunks. For PDF files, this triggers the multi-channel pipeline (text, tables, and images).

```bash
curl -X POST "http://localhost/api/data/process/my_project" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_size": 500,
    "overlap_size": 120,
    "do_reset": false
  }'
```

#### Step 3: Generate & Store Embeddings (`POST /api/nlp/embed/{project_name}`)
Generate vector embeddings for all chunks and store them in the configured Vector DB (Qdrant or pgvector).

```bash
curl -X POST "http://localhost/api/nlp/embed/my_project" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "do_reset": false
  }'
```

#### Step 4: Ask Questions (`POST /api/nlp/answer/{project_name}`)
Perform semantic retrieval across vector embeddings and generate an AI-powered answer using the configured LLM.

```bash
curl -X POST "http://localhost/api/nlp/answer/my_project" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the key takeaways from the document?",
    "top_k": 4,
    "response_language": "auto"
  }'
```

> **Interactive Documentation**: FastAPI's interactive Swagger UI is also accessible at `http://localhost/docs` (or `http://localhost:8797/docs` when running directly on the application port).

---

## Observability & Metrics

`mini-RAG` provides full metrics exposure for Prometheus monitoring.

- **FastAPI Metrics Endpoint**: `http://localhost/metrics` (or `http://localhost:8797/metrics`)
- **Prometheus Web UI**: `http://localhost:9090`
- **Grafana Web UI**: `http://localhost:3000` *(Default login: `admin` / `admin_password`)*
- **Qdrant Dashboard**: `http://localhost:6333/dashboard`

All Grafana dashboards (FastAPI, PostgreSQL, Qdrant, Node Exporter) and the Prometheus data source are **auto-provisioned** on startup — no manual import or configuration required.

---

## Project Structure

```text
mini-RAG/
├── docker/                 # Docker Compose, Nginx, Prometheus, & Grafana configs
│   ├── app/                # Dockerfile for FastAPI app
│   ├── env/                # Environment template files (.env.app, .env.postgres, etc.)
│   ├── nginx/              # Nginx reverse proxy configuration
│   ├── grafana/             # Grafana provisioning (datasources & dashboards)
│   ├── prometheus/         # Prometheus scrape configuration
│   └── README.md           # Full Docker deployment guide
├── postman/                # Postman API Collection
│   └── mini-rag-v1.0.0-api.postman_collection.json
├── src/
│   ├── controllers/        # Business logic for Data, Process, and NLP
│   ├── ingestion/          # Document loaders & production PDF processing pipeline
│   │   ├── chunkers/       # Text chunking strategies
│   │   ├── loaders/        # Custom format loaders (.pdf, .docx, .html, .md, .txt)
│   │   └── pdf_pipeline/   # Multi-channel layout & VLM OCR parser for PDFs
│   ├── models/             # Database, Vector DB, and request Pydantic schemas
│   ├── routes/             # FastAPI routers (/data, /nlp)
│   ├── services/           # LLM and Vector DB client adapters
│   ├── utils/              # Config, logging, and metrics exporter setup
│   └── main.py             # FastAPI entrypoint
├── pyproject.toml          # uv project dependencies
└── README.md               # Main project documentation
```

---

## License

This project is open-source and licensed under the [MIT License](file:///home/ahmed-hasan110/Desktop/code/Projects/mini-RAG/LICENSE).
