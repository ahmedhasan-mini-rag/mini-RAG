FILE_ALLOWED_TYPES=["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/html", "text/markdown"]
FILE_MAX_SIZE=10
FILE_CHUNK_SIZE=512000 # 512 KB

POSTGRES_PORT=5432
POSTGRES_HOST=pgvector # docker compose service name

# llms settings

CHAT_MODEL_PROVIDER="cohere"
EMBEDDING_MODEL_PROVIDER="cohere"

OPENAI_API_KEY=
OPENAI_BASE_URL=
COHERE_API_KEY=
GOOGLE_API_KEY=

CHAT_MODEL_ID=
EMBEDDING_MODEL_ID=

# note that some embedding model don't support specifying the embedding size
# in this case, comment out the 'EMBEDDING_SIZE' field below to avoid errors
# EMBEDDING_SIZE=

DEFAULT_MAX_OUTPUT_TOKENS=1200
DEFAULT_MAX_INPUT_CHARS=2200
DEFAULT_TEMPERATURE=0.5

# vector dbs settings

VECTORDB_PROVIDER=
VECTORDB_SIMILARITY_METRIC="cosine"
VECTORDB_INDEX_BUILDING_THRESHOLD=10000  # threshold after which to start building the vector index
VECTORDB_INDEX_TYPE="hnsw"

# qdrant container connection (set QDRANT_HOST to use the qdrant container, leave empty for embedded mode)
QDRANT_HOST="qdrant"  # docker compose service name
QDRANT_PORT=6333

# pdf processing settings

SCANNED_PAGE_TEXT_MAX_LIMIT=
SCANNED_PAGE_MIN_RATIO_LIMIT=
CONVERSION_DPI=

## you can use ollama or HF
OCR_MODEL_ID=
OCR_MODEL_URL=
OCR_MODEL_API_KEY="ollama"
MAX_CONCURRENT_VLM_CALLS=5

# images cloudflare storage settings

R2_BUCKET_NAME=
R2_ACCOUNT_ID=
R2_PUBLIC_URL=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=

# celery settings

CELERY_TASK_SERIALIZER="json"
CELERY_TASK_TIME_LIMIT=
CELERY_TASK_ACKS_LATE=
CELERY_TASK_WORKER_CONCURRENCY=

# celery broker(rabbitmq) and results backend(redis) settings

RABBITMQ_HOST="rabbitmq"
RABBITMQ_PORT=5672

REDIS_HOST="redis"
REDIS_PORT=6379

# flower pass
CELERY_FLOWER_PASS=

TASK_EXECUTION_TABLE_RETENTION_TIME=86400