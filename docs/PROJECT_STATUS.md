# CloudMentor AI — Project Status

This document records the implementation status of CloudMentor AI at a specific point in Git history. It complements the public overview in [`README.md`](../README.md); it is not a daily development log or a replacement for issues and pull requests.

## Status snapshot

| Field | Value |
| --- | --- |
| Snapshot date | 2026-10-16 |
| Application baseline | `20656d0ac9dd2f372314a215d93bc6a80df1a8f4` |
| Current milestone | Reproducible subject-scoped local RAG lifecycle |
| Overall state | Core local lifecycle is manually verified and covered by an automated application-level test; durable source storage, recovery, and evaluation hardening remain |
| CI evidence | GitHub Actions checks passed for PR #18 and PR #19 |

The status was captured against `main` at `20656d0ac9dd2f372314a215d93bc6a80df1a8f4` before this update receives its own commit.

## Current capability

CloudMentor AI currently contains the components required for this local workflow:

```text
create subject
    -> upload PDF
    -> extract, clean, chunk, embed, and index
    -> track document lifecycle in PostgreSQL
    -> ask a question within the selected subject
    -> return an answer constrained by retrieved context
    -> show document and page references
    -> delete the document from active use
```

This complete sequence passed a manual local end-to-end test on 2026-10-07. It is now also covered by `tests/test_document_lifecycle_e2e.py`, which exercises the real FastAPI routes, repositories, lifecycle orchestration, and an isolated temporary Chroma index. External PDF extraction, embedding, and answer generation are replaced with deterministic test doubles, so live external-service integration remains a separate boundary.

## Capability matrix

| Area | Status | Evidence or boundary |
| --- | --- | --- |
| Subject creation and listing | Implemented | API and repository tests; manual frontend smoke test |
| PDF validation and upload | Implemented | Upload API tests cover type, signature, filename, and size boundaries |
| Page-level extraction and cleaning | Implemented | Loader and transformation tests |
| Overlapping chunk generation | Implemented | Chunk boundaries, overlap, indices, and metadata tests |
| PostgreSQL document lifecycle | Implemented | `UPLOADED`, `PROCESSING`, `INDEXED`, and `FAILED` states |
| Subject metadata propagation | Implemented | Metadata flows through document, chunk, vector, retrieval, and chat layers |
| Subject-scoped retrieval | Implemented | Retriever and chat orchestration tests; manual smoke test |
| Answer and source rendering | Implemented | Frontend renders context-constrained answers with document/page references |
| Legacy `subject_id` backfill | Completed locally | Dry run found 223 missing values; apply updated them; second dry run found 0 |
| Automated Chroma rebuild | Not implemented | Recovery roadmap item |
| Cross-store reconciliation | Not implemented | PostgreSQL-Chroma consistency roadmap item |
| Retrieval and answer benchmark | Not implemented | No measured relevance, citation-correctness, or faithfulness baseline |
| Production operations | Not implemented | Authentication, authorization, monitoring, and deployment remain out of scope |
| Embedding and Chroma indexing | Implemented locally | Automated lifecycle coverage uses deterministic embeddings with an isolated real Chroma index; live external embedding integration remains outside CI |
| Document deletion | Implemented and automatically covered | The lifecycle test verifies Chroma removal, PostgreSQL `DELETED` state, and that the deleted document is no longer retrieved; the real local workflow also passed manually |

## Verification evidence

### Automated

- The full backend suite passed locally with `61 passed` and one dependency deprecation warning.
- `tests/test_document_lifecycle_e2e.py` covers subject creation, upload, `INDEXED` state, subject-scoped retrieval with source lineage, deletion, PostgreSQL lifecycle state, Chroma removal, and post-delete retrieval behavior.
- The lifecycle test uses SQLite in memory and an isolated temporary Chroma directory.
- Deterministic test doubles replace external PDF extraction, embedding, and answer generation.
- The lifecycle test was introduced by commit `3f27b7a320ccbc08cc6396abbb852a9faca7b40f` and merged through PR #18.
- GitHub Actions backend and frontend checks passed for PR #18 and PR #19.

### Manual local end-to-end

Verified on 2026-10-07 against commit `89fd45d`:

- Created a new subject.
- Uploaded a new PDF.
- Observed the document reach `INDEXED`.
- Asked a question whose answer was contained in that PDF.
- Received an answer with the expected filename and page reference.
- Deleted the document.
- Repeated the question and confirmed that the deleted document was no longer returned by retrieval.

Result: **passed**.

The legacy Chroma metadata migration was also verified separately with dry run, apply, and a no-op second dry run.

## Data ownership boundary

| Data | Current owner | Current limitation |
| --- | --- | --- |
| Subject and document metadata | PostgreSQL | No production backup or restore procedure yet |
| Document lifecycle state | PostgreSQL | No automated cross-store reconciliation yet |
| Accepted source PDFs | Local upload storage | Not durable production storage |
| Chunk vectors and retrieval metadata | Chroma | Derived index without an automated rebuild workflow |
| Generated answers | API response | Not treated as a durable application record |

PostgreSQL is the system of record for metadata and lifecycle state. Chroma is a derived retrieval index. A dependable Chroma rebuild still requires durable canonical content and an implemented, tested rebuild procedure.

## Known limitations

- Source PDFs are retained locally instead of in durable object storage.
- Ingestion is not fully idempotent across retries and partial failures.
- Chroma rebuilding and PostgreSQL-Chroma reconciliation are manual roadmap work.
- Retrieval relevance, citation correctness, and answer faithfulness are not benchmarked.
- CI does not run live PostgreSQL, Chroma, embedding, and Gemini as one integration workflow.
- Dedicated health and readiness endpoints are not implemented.
- Structured operational logging, metrics, tracing, and alerting are incomplete.
- Authentication, authorization, rate limiting, and production deployment are not implemented.

## Next milestone priorities

1. Define durable canonical content storage and record source URI, checksum, and file-size metadata.
2. Make ingestion idempotent across retries and partial failures.
3. Implement Chroma rebuild and PostgreSQL-Chroma reconciliation workflows.
4. Create a small retrieval and answer-quality evaluation dataset.
5. Add health checks and structured operational diagnostics.

## Update policy

Update this document when a milestone changes, a limitation is removed, or new verification evidence is produced. Every update should include:

- the snapshot date;
- the application commit or release being described;
- links or stable identifiers for reproducible CI or test evidence;
- capabilities added or removed;
- known limitations that changed;
- the next milestone priorities.

Use Git history, pull requests, and issues for chronological development activity. Do not turn this file into a running activity log.
