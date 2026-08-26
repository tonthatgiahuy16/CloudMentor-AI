# CloudMentor AI

> An in-progress document-data backbone for RAG applications, built around modular PDF ingestion, traceable metadata, PostgreSQL lifecycle records, and a rebuildable Chroma index.

CloudMentor AI is a personal project I am building as a final-year Data Science student. It explores how raw learning documents can be converted into structured, traceable data that backend services and LLM-based applications can use reliably.

The current focus is the **data backbone**: ingestion stages, metadata propagation, storage boundaries, retrieval, and validation. The LLM is a downstream consumer of this pipeline rather than the center of the architecture.

## What this project demonstrates

- A modular **Extract -> Transform -> Chunk -> Embed -> Index** ingestion flow.
- Page- and chunk-level metadata carried from the source PDF into retrieval results.
- A dual-store design in which PostgreSQL represents canonical lifecycle data and Chroma acts as a rebuildable retrieval index.
- Clear boundaries between ingestion, persistence, retrieval, API, and generation components.
- Stage-level validation while the project moves toward repeatable automated tests.

## Current status

The repository contains a working ingestion and retrieval foundation, but it is **not a production system**. PostgreSQL models and migrations exist; their full integration into the upload and retrieval lifecycle is still in progress.

### Implemented

- FastAPI endpoints for PDF upload and chat requests.
- PDF text extraction with page-level metadata.
- Transformation and chunking stages with traceable document metadata.
- BGE-M3 embeddings and persistent Chroma storage.
- Retrieval results containing `document_id`, `chunk_index`, page, source, and distance metadata.
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

## Data Engineering backbone

### 1. Ingestion

The upload API accepts a PDF and passes it through explicit pipeline stages. Each stage has a focused responsibility, making the flow easier to validate and extend.

```text
PDF upload
   -> Extract text by page
   -> Transform text
   -> Create chunks and metadata
   -> Generate embeddings
   -> Index vectors for retrieval
```

### 2. Traceability

Metadata is preserved through ingestion and retrieval so an answer can be traced back to its source. The current retrieval path exposes:

- `document_id`
- `chunk_index`
- page
- source
- vector distance

This provides the foundation for source-grounded answers, document-level filtering, deletion, and later quality evaluation.

### 3. Storage boundaries

The two storage systems serve different purposes:

| Store | Responsibility | Current state |
| --- | --- | --- |
| PostgreSQL | Canonical subject and document lifecycle records | Models and Alembic migrations implemented; service integration in progress |
| Chroma | Persistent embeddings and retrieval metadata | Implemented in the current ingestion and retrieval path |

PostgreSQL is intended to remain the source of truth for document lifecycle data. Chroma is treated as a derived index that can be reconciled or rebuilt from canonical records.

### 4. Serving and consumption

FastAPI exposes the pipeline to clients. For a chat request, the system embeds the question, retrieves relevant chunks and passes only the retrieved context to Gemini. The response includes source information from the retrieval layer.

### 5. Reliability work

The project currently uses manual scripts to validate individual stages. The next reliability milestones are automated tests, safer upload handling, document deletion, and reconciliation between PostgreSQL and Chroma.

## Current architecture

```mermaid
flowchart LR
    U[PDF upload] --> API[FastAPI upload service]
    API --> EX[Extract by page]
    EX --> TR[Transform text]
    TR --> CK[Chunk + metadata]
    CK --> EM[BGE-M3 embeddings]
    EM --> CH[(Chroma index)]

    API -. lifecycle integration in progress .-> PG[(PostgreSQL)]

    Q[Question] --> QE[Query embedding]
    QE --> RT[Retriever]
    CH --> RT
    RT --> GM[Gemini]
    GM --> A[Answer + sources]
```

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

- PostgreSQL lifecycle models are not yet fully connected to the service flow.
- The upload endpoint still needs filename sanitization and stronger PDF validation.
- Validation scripts are not yet a reliable automated test suite.
- The project currently requires local PostgreSQL and a Gemini API key.
- Retrieval quality has not yet been evaluated against a curated benchmark.
- Chroma reconciliation and document deletion are not yet implemented.

## Roadmap

1. Finish PostgreSQL lifecycle integration.
2. Add idempotent ingestion and document-level duplicate detection.
3. Add document deletion and PostgreSQL-Chroma reconciliation.
4. Add pytest unit and integration tests.
5. Add Docker Compose and health checks.
6. Build a small retrieval-evaluation dataset.
7. Consider Kafka or Spark only when the workflow has a justified event-processing or analytics requirement.

## Author

**Tôn Thất Gia Huy**  
Final-year Data Science student, expected graduation in 2027.

- [Portfolio](https://tonthatgiahuy16.github.io)
- [GitHub](https://github.com/tonthatgiahuy16)
- [LinkedIn](https://www.linkedin.com/in/t%C3%B4n-th%E1%BA%A5t-gia-huy-708860369/)

