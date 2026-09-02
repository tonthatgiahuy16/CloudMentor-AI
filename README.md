# CloudMentor AI

[![Tests](https://github.com/tonthatgiahuy16/CloudMentor-AI/actions/workflows/tests.yml/badge.svg)](https://github.com/tonthatgiahuy16/CloudMentor-AI/actions/workflows/tests.yml)

> An in-progress document-data backbone for RAG applications, built around modular PDF ingestion, traceable metadata, PostgreSQL lifecycle records, and a rebuildable Chroma index.

CloudMentor AI is a personal project I am building as a final-year Data Science student. It explores how learning documents can be converted into structured, traceable data for backend services and LLM-based applications.

The main focus is the **data backbone**: ingestion stages, metadata propagation, storage boundaries, retrieval, validation, and testability. The LLM is a downstream consumer rather than the center of the architecture.

## What this project demonstrates

- A modular **Extract -> Transform -> Chunk -> Embed -> Index** ingestion flow.
- Page- and chunk-level lineage carried from each PDF into retrieval results.
- PostgreSQL as the planned source of truth for document lifecycle data and Chroma as a derived retrieval index.
- Clear boundaries between ingestion, persistence, retrieval, API, and generation components.
- Dependency-injected chat orchestration that can be tested without live model services.
- Automated unit and API tests running in GitHub Actions.

## Current status

The repository contains a working ingestion and retrieval foundation, but it is **not a production system**.

### Implemented

- FastAPI endpoints for PDF upload and chat requests.
- PDF extraction, text cleaning, overlapping chunking, embeddings, and persistent Chroma indexing.
- Retrieval results containing `document_id`, `chunk_index`, page, source, and vector distance.
- Gemini-based answer generation using retrieved context.
- PostgreSQL models and Alembic migration groundwork for subjects and documents.
- Safer PDF upload handling: extension, MIME type, file signature, filename, and 10 MB size checks.
- UUID-prefixed server filenames and cleanup when ingestion fails.
- Input validation for chat questions and chunk configuration.
- Pytest coverage for cleaning, loading, chunking, transformation, retrieval, chat orchestration, schemas, and upload validation.
- GitHub Actions checks for Python syntax and tests on pushes and pull requests.

### In progress

- Connecting PostgreSQL lifecycle records to the upload and retrieval services.
- Integration tests for PostgreSQL, Chroma, embedding, and Gemini boundaries.
- Document deletion and PostgreSQL-Chroma reconciliation.
- A reproducible local environment with Docker Compose and health checks.
- A small retrieval-quality benchmark.

### Deliberately not claimed

- Production deployment or operational monitoring.
- Kafka or Spark processing without a justified workload.
- Quiz, learning-history, or ML-personalization features.

## Data flow

```text
PDF upload
   -> validate and store safely
   -> extract text by page
   -> normalize text
   -> create overlapping chunks + lineage metadata
   -> generate BGE-M3 embeddings
   -> index in Chroma

Question
   -> embed query
   -> retrieve relevant chunks
   -> generate answer with Gemini
   -> return answer + sources
```

## Traceability

Every retrieval result keeps enough metadata to trace an answer back to its source:

- `document_id`
- `chunk_index`
- page
- source filename
- vector distance

This is the foundation for source-grounded answers, document-level filtering, deletion, and later retrieval evaluation.

## Storage boundaries

| Store | Responsibility | Current state |
| --- | --- | --- |
| PostgreSQL | Canonical subject and document lifecycle records | Models and Alembic migrations exist; service integration is in progress |
| Chroma | Persistent embeddings and retrieval metadata | Used by the current ingestion and retrieval path |

The intended design treats Chroma as a rebuildable index, not the canonical record of uploaded documents.

## Architecture

```mermaid
flowchart LR
    U[PDF upload] --> V[Validation]
    V --> EX[Extract by page]
    EX --> TR[Normalize text]
    TR --> CK[Chunk + lineage]
    CK --> EM[BGE-M3 embeddings]
    EM --> CH[(Chroma index)]

    V -. lifecycle integration in progress .-> PG[(PostgreSQL)]

    Q[Question] --> QE[Query embedding]
    QE --> RT[Retriever]
    CH --> RT
    RT --> GM[Gemini]
    GM --> A[Answer + sources]
```

## Repository structure

```text
CloudMentor-AI/
├── .github/workflows/   # CI test workflow
├── app/
│   ├── api/             # FastAPI routes and request validation
│   ├── core/            # Configuration, database, and logging
│   ├── db_models/       # SQLAlchemy models
│   ├── llm/             # Gemini client and prompts
│   ├── models/          # Pipeline data models
│   ├── pipeline/        # Ingestion stages
│   ├── rag/             # Loader, chunker, embeddings, index, retrieval
│   └── services/        # Upload and chat orchestration
├── alembic/             # Database migrations
├── scripts/             # Manual service probes
├── tests/               # Isolated pytest unit and API tests
├── requirements.txt
└── requirements-test.txt
```

## Local setup

Create and activate a virtual environment, then install the application dependencies:

```bash
python -m venv .venv
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set local values:

```env
DATABASE_URL=postgresql+psycopg://cloudmentor:cloudmentor@localhost:5432/cloudmentor
GEMINI_API_KEY=replace_with_your_key
MODEL_NAME=gemini-2.5-flash
```

Run migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API documentation.

## Tests

The automated suite is isolated from live PostgreSQL, Chroma, embedding-model, and Gemini services.

```bash
pip install -r requirements-test.txt
pytest -q
```

The same checks run in GitHub Actions. Live-service integration and retrieval-quality evaluation remain separate milestones.

## Known limitations

- PostgreSQL lifecycle models are not fully connected to the service flow.
- There is no transaction or compensation strategy across PostgreSQL and Chroma yet.
- Live Chroma, embedding, Gemini, and PostgreSQL integration is not covered by CI.
- Retrieval quality has not been measured against a curated benchmark.
- Docker Compose, health checks, deployment, and monitoring are not implemented.

## Roadmap

1. Finish PostgreSQL lifecycle integration.
2. Add idempotent ingestion and document-level duplicate detection.
3. Add deletion and PostgreSQL-Chroma reconciliation.
4. Add live-service integration tests.
5. Add Docker Compose and health checks.
6. Build a retrieval-evaluation dataset and track grounding quality.

## Author

**Tôn Thất Gia Huy**  
Final-year Data Science student, expected graduation in 2027.

- [Portfolio](https://tonthatgiahuy16.github.io)
- [GitHub](https://github.com/tonthatgiahuy16)
- [LinkedIn](https://www.linkedin.com/in/t%C3%B4n-th%E1%BA%A5t-gia-huy-708860369/)
