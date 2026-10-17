# CloudMentor AI — Project Status

This document records the implementation status of CloudMentor AI at a specific point in Git history. It complements the public overview in [`README.md`](../README.md); it is not a daily development log or a replacement for issues and pull requests.

## Status snapshot

| Field | Value |
| --- | --- |
| Snapshot date | 2026-10-17 |
| Application baseline | `49fd465185d76918802626ab228308a0ebe0346b` |
| Current milestone | Recoverable subject-scoped local RAG lifecycle |
| Overall state | The local PDF lifecycle now retains canonical source metadata, supports duplicate-safe retries, stale-ingestion recovery, subject trash and restore, and guarded legacy-source repair; durable object storage, automated cross-store reconciliation, multi-source ingestion, and retrieval evaluation remain |
| CI evidence | GitHub Actions backend and frontend checks passed for PRs #21 through #26 |

The status was captured against `main` at `49fd465185d76918802626ab228308a0ebe0346b` before this documentation update receives its own commit.

## Current capability

CloudMentor AI currently supports this local workflow:

```text
create subject
    -> validate and retain a canonical PDF
    -> record source URI, SHA-256, and file size in PostgreSQL
    -> reject an active duplicate or retry a failed ingestion with the same identity
    -> extract, clean, chunk, embed, and index
    -> track document lifecycle and processing activity in PostgreSQL
    -> ask a question within the selected subject
    -> return an answer constrained by retrieved context
    -> show document and page references
    -> either delete a document from active use
       or move a subject to Trash
           -> remove its derived Chroma vectors
           -> retain PostgreSQL metadata and source PDFs
           -> restore the subject by rebuilding Chroma
```

Operational recovery paths also exist for stale ingestions and for legacy document rows whose retained-source metadata is missing. Both workflows preserve the existing document identity, and the legacy repair command defaults to dry run before any filesystem or PostgreSQL change.

The core application lifecycle remains covered by `tests/test_document_lifecycle_e2e.py`, which exercises real FastAPI routes, repositories, lifecycle orchestration, and an isolated temporary Chroma index. Deterministic test doubles replace external extraction, embedding, and answer generation at that boundary, while focused repository, service, API, and CLI tests cover duplicate handling, stale recovery, subject trash and restore, and legacy-source repair.

A live local recovery was verified on 2026-10-17 against the application state merged through PR #26. A legacy BigData document retained its original `document_id`, received verified source metadata, restored its subject to `ACTIVE`, reached `INDEXED`, rebuilt 12 subject-scoped Chroma chunks, and produced a RAG answer citing `BigData_Lec06.pdf` pages 3, 4, and 6.

## Capability matrix

| Area | Status | Evidence or boundary |
| --- | --- | --- |
| Subject creation and active listing | Implemented | API, repository, and frontend verification |
| Subject trash and restore lifecycle | Implemented and automatically covered | Lifecycle states, failure recording, Chroma removal, retained-source rebuild, API tests, service tests, and live UI verification |
| PDF validation and upload | Implemented | Upload API tests cover type, signature, filename, and size boundaries |
| Canonical PDF source metadata | Implemented locally | PostgreSQL records `source_uri`, `content_sha256`, and `file_size_bytes`; storage remains local rather than production-durable |
| Page-level extraction and cleaning | Implemented | Loader and transformation tests |
| Overlapping chunk generation | Implemented | Chunk boundaries, overlap, indices, and metadata tests |
| PostgreSQL document lifecycle | Implemented | `UPLOADED`, `PROCESSING`, `INDEXED`, `FAILED`, and `DELETED` states plus processing attempts, heartbeat, and stage metadata |
| Duplicate-safe ingestion and failed retry | Implemented for sequential requests | Active duplicates are rejected; failed ingestion retries reuse retained source and document identity; concurrent-request uniqueness is not yet enforced |
| Stale-ingestion recovery | Implemented operator workflow | Stale selection, processing heartbeat, dry-run/apply CLI, failure handling, and automated tests |
| Subject metadata propagation | Implemented | Metadata flows through document, chunk, vector, retrieval, and chat layers |
| Subject-scoped retrieval | Implemented | Retriever and chat orchestration tests plus live local verification |
| Answer and source rendering | Implemented | Frontend renders context-constrained answers with document and page references |
| Document deletion | Implemented and automatically covered | Tests verify Chroma removal, PostgreSQL `DELETED` state, and post-delete retrieval behavior |
| Retained-source Chroma rebuild | Implemented through subject restore | Automated service tests and a live restore rebuilt 12 subject-scoped chunks from the retained PDF |
| Guarded legacy-source repair | Implemented operator workflow | Dry-run-first CLI, checksum and size verification, conflict protection, idempotent rerun tests, and live recovery evidence |
| Legacy `subject_id` backfill | Completed locally | Dry run found 223 missing values; apply updated them; second dry run found 0 |
| Cross-store reconciliation | Not implemented | PostgreSQL–Chroma comparison and automated repair remain roadmap work |
| Retrieval and answer benchmark | Not implemented | No measured relevance, citation-correctness, or faithfulness baseline |
| Production operations | Not implemented | Authentication, authorization, monitoring, durable object storage, and deployment remain out of scope |

## Verification evidence

### Automated

- The full backend suite passed locally with `145 passed` and one existing Starlette `TestClient` dependency deprecation warning.
- `tests/test_document_lifecycle_e2e.py` covers subject creation, upload, `INDEXED` state, subject-scoped retrieval with source lineage, deletion, PostgreSQL lifecycle state, Chroma removal, repeated upload behavior, and failed-document retry.
- The lifecycle test uses SQLite in memory, an isolated temporary Chroma directory, and deterministic test doubles at external extraction, embedding, and answer-generation boundaries.
- Repository, service, API, and CLI tests cover canonical source metadata, sequential duplicate protection, retained-source retry, processing heartbeats, stale-ingestion recovery, subject trash and restore, and guarded legacy-source repair.
- Legacy-source repair tests cover dry run, explicit apply, source changes after planning, conflicting target files, conflicting PostgreSQL metadata, missing documents, and idempotent reruns.
- GitHub Actions backend and frontend checks passed for PRs #21 through #26.
- CI does not run live PostgreSQL, Chroma, embedding, and Gemini together as one external integration workflow.

### Manual local end-to-end

Verified on 2026-10-17 against `main` at `49fd465185d76918802626ab228308a0ebe0346b`:

- Identified a legacy BigData document whose restore correctly failed because retained-source metadata was incomplete.
- Supplied the original `BigData_Lec06.pdf` through the dry-run-first repair workflow.
- Verified the canonical file size as `1,061,675` bytes and SHA-256 as `70787cfc74d99d961d53fbb9fa63757abe2c0fb165548c412799086ba91b680e`.
- Attached source metadata while preserving the existing `document_id`.
- Restored the subject to `ACTIVE` and the document to `INDEXED`.
- Rebuilt 12 Chroma chunks, all scoped to the expected subject.
- Asked a live RAG question and received an answer citing `BigData_Lec06.pdf` pages 3, 4, and 6.

Result: **passed**.

An earlier local lifecycle verification on 2026-10-07 covered create subject, upload PDF, reach `INDEXED`, retrieve an answer with a source reference, delete the document, and confirm it was no longer retrieved.

The legacy Chroma `subject_id` metadata migration was also verified separately with dry run, apply, and a no-op second dry run.

## Data ownership boundary

| Data | Current owner | Current limitation |
| --- | --- | --- |
| Subject and document metadata | PostgreSQL | No production backup or restore procedure yet |
| Document and subject lifecycle state | PostgreSQL | Recovery workflows are operator-invoked rather than scheduled |
| Accepted source PDFs | Local canonical upload storage | Rebuildable locally, but not durable across machine or disk loss |
| Chunk vectors and retrieval metadata | Chroma | Derived and rebuildable when retained source metadata is complete; automated cross-store reconciliation is not implemented |
| Generated answers | API response | Not treated as a durable application record |

PostgreSQL is the system of record for identity, metadata, and lifecycle state. Chroma is a derived retrieval index. Chroma can now be rebuilt through subject restore when a valid retained source exists. The current recovery guarantee remains local because canonical PDFs are stored on the application machine rather than in durable object storage.

## Known limitations

- Canonical source PDFs are retained locally instead of in durable object storage.
- Duplicate-safe behavior covers sequential requests and failed retries; concurrent-request uniqueness is not enforced at the database level.
- Stale-ingestion recovery and legacy-source repair require an operator to run a CLI or initiate restore.
- PostgreSQL–Chroma reconciliation is not implemented, so drift is not automatically detected or repaired.
- Legacy documents without source metadata still require the operator to locate and supply the correct original PDF.
- PDF is the only supported ingestion format; TXT and DOCX are not implemented under the common document contract.
- Retrieval relevance, citation correctness, and answer faithfulness are not benchmarked.
- CI does not run live PostgreSQL, Chroma, embedding, and Gemini as one integration workflow.
- Dedicated health and readiness endpoints are not implemented.
- Structured operational logging, metrics, tracing, and alerting are incomplete.
- Authentication, authorization, rate limiting, and production deployment are not implemented.

## Next milestone priorities

1. Implement PostgreSQL–Chroma reconciliation with dry-run reporting, document- and subject-scoped drift detection, and guarded repair.
2. Move canonical source retention from local disk to durable object storage with backup and retention policies.
3. Extend the document contract and ingestion pipeline to support TXT and DOCX.
4. Add database-level protection for concurrent duplicate ingestion and schedule stale-ingestion recovery.
5. Create a small retrieval and answer-quality evaluation dataset with relevance, citation-correctness, and faithfulness checks.
6. Add health checks and structured operational diagnostics.

## Update policy

Update this document when a milestone changes, a limitation is removed, or new verification evidence is produced. Every update should include:

- the snapshot date;
- the application commit or release being described;
- links or stable identifiers for reproducible CI or test evidence;
- capabilities added or removed;
- known limitations that changed;
- the next milestone priorities.

Use Git history, pull requests, and issues for chronological development activity. Do not turn this file into a running activity log.
