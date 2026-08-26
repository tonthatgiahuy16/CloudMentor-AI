# CloudMentor AI

> An in-progress RAG API prototype for turning uploaded learning PDFs into traceable, source-grounded answers.

CloudMentor AI is a personal project I am building as a final-year Data Science student. The goal is to learn how document ingestion, backend APIs, relational metadata, vector retrieval, and LLM generation fit together in one maintainable application.

## Current status

The repository contains a working application foundation, but it is **not a production system**. The current implementation focuses on the document-ingestion and retrieval path.

### Implemented

- FastAPI endpoints for PDF upload and chat requests.
- Modular ingestion flow: **Extract -> Transform -> Chunk -> Embed -> Index**.
- PDF text extraction with page-level metadata.
- BGE-M3 embeddings and persistent Chroma storage.
- Retrieval with `document_id`, `chunk_index`, page, source, and distance metadata.
- Gemini-based answer generation using retrieved context.
- PostgreSQL models and Alembic migration groundwork for subjects and documents.
- Manual validation scripts for loading, chunking, embedding, retrieval, and chat behavior.

### In progress

- Connecting PostgreSQL lifecycle records to the upload and retrieval services.
- Replacing manual validation scripts with repeatable pytest tests.
- Adding safer upload handling, structured error responses, and health checks.
- Creating a reproducible local environment with Docker Compose.

### Not implemented yet

- Quiz and learning-history features.
- Kafka event processing.
- Spark analytics.
- Machine-learning personalization.
- Production deployment, CI/CD, and operational monitoring.

## Current architecture

```mermaid
flowchart LR
    U[PDF upload] --> API[FastAPI]
    API --> EX[Extract]
    EX --> TR[Transform]
    TR --> CK[Chunk + metadata]
    CK --> EM[BGE-M3 embeddings]
    EM --> CH[(Chroma)]

    Q[Question] --> QE[Query embedding]
    QE --> RT[Retriever]
    RT --> CH
    RT --> GM[Gemini]
    GM --> A[Answer + sources]

    PG[(PostgreSQL)] -. lifecycle foundation .-> API
```

The intended boundary is straightforward: PostgreSQL will hold canonical document lifecycle data, while Chroma remains a rebuildable retrieval index.

## Repository structure

```text
CloudMentor-AI/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Configuration, database, and logging
│   ├── db_models/        # SQLAlchemy models
│   ├── llm/              # Gemini client and prompts
│   ├── models/           # Pipeline data models
│   ├── pipeline/         # Ingestion stages
│   ├── rag/              # Loader, chunker, embeddings, Chroma, retrieval
│   └── services/         # Upload and chat orchestration
├── alembic/              # Database migrations
├── scripts/              # Manual validation utilities
├── tests/                # Validation scripts being migrated to pytest
├── .env.example
├── alembic.ini
└── requirements.txt
```

## Local setup

### 1. Create an environment

```bash
python -m venv .venv
```

Activate it, then install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and provide your local PostgreSQL connection and Gemini API key.

```env
DATABASE_URL=postgresql+psycopg://cloudmentor:cloudmentor@localhost:5432/cloudmentor
GEMINI_API_KEY=replace_with_your_key
MODEL_NAME=gemini-2.5-flash
```

Never commit the populated `.env` file.

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to inspect the API.

## Known limitations

- The upload endpoint still needs filename sanitization and stronger PDF validation.
- PostgreSQL lifecycle models are present but are not fully integrated into the service flow.
- Validation scripts are not yet a reliable automated test suite.
- The project currently requires local PostgreSQL and a Gemini API key.
- Retrieval quality has not yet been evaluated against a curated benchmark.

## Roadmap

1. Finish PostgreSQL lifecycle integration.
2. Add pytest unit and integration tests.
3. Add Docker Compose and health checks.
4. Build a small retrieval-evaluation dataset.
5. Add document deletion and Chroma reconciliation.
6. Consider Kafka or Spark only when the product workflow justifies them.

## Author

**Tôn Thất Gia Huy**  
Final-year Data Science student, expected graduation in 2027.

- [Portfolio](https://tonthatgiahuy16.github.io)
- [GitHub](https://github.com/tonthatgiahuy16)
- [LinkedIn](https://www.linkedin.com/in/t%C3%B4n-th%E1%BA%A5t-gia-huy-708860369/)

