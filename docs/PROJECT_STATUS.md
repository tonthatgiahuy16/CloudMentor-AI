# CloudMentor AI — Project Status

This document records the implementation status of CloudMentor AI at a specific point in Git history. It complements the public overview in [`README.md`](../README.md); it is not a daily development log or a replacement for issues and pull requests.

## Status snapshot

| Field | Value |
| --- | --- |
| Snapshot date | 2026-10-19 |
| Application baseline | `e0d6afbef4fce5beef0b8008d144da5f843d6324` |
| Current milestone | Phase 2 locked: recoverable multi-format subject-scoped local RAG lifecycle |
| Overall state | PDF, UTF-8 TXT, and body-paragraph DOCX now have a locally recoverable lifecycle; upload and retained-source validation use an injectable local source-storage boundary; path-independent extraction, durable object storage, concurrent duplicate protection, automated drift repair, and retrieval evaluation remain |
| CI evidence | GitHub Actions backend and frontend checks passed through PR #30; `main` at `e0d6afb` is locally verified with 245 backend tests, frontend lint and build, and a live TXT recovery cycle |

The status was captured against `main` at `e0d6afbef4fce5beef0b8008d144da5f843d6324` before this documentation update receives its own commit.

## Current capability

CloudMentor AI currently supports this local workflow:

```text
create subject
    -> validate and retain a canonical PDF, UTF-8 TXT, or body-paragraph DOCX through the local source-storage boundary
    -> record source URI, SHA-256, and file size in PostgreSQL
    -> reject an active duplicate or retry a failed ingestion with the same identity
    -> extract, clean, and preserve page, line, or paragraph boundaries
    -> chunk, embed, and index with format-aware source metadata
    -> track document lifecycle and processing activity in PostgreSQL
    -> ask a question within the selected subject
    -> return an answer constrained by retrieved context
    -> show document and page, line-range, or paragraph-range references
    -> either delete a document from active use
       or move a subject to Trash
           -> remove its derived Chroma vectors
           -> retain PostgreSQL metadata and canonical source files
           -> restore the subject by rebuilding Chroma
```

Operational recovery paths also exist for stale ingestions and for legacy document rows whose retained-source metadata is missing. Both workflows preserve the existing document identity, and the legacy repair command defaults to dry run before any filesystem or PostgreSQL change.

Canonical source writes and retained-source validation now use an injectable source-storage interface, with `LocalSourceStorage` as the first implementation. The remaining extraction path still consumes `source_uri` as a local filesystem path, so a remote object store is not yet a drop-in replacement; path-independent reads or controlled local materialization must be completed before adding MinIO.

A read-only PostgreSQL-Chroma reconciliation workflow compares the relational lifecycle registry with the derived vector index. It reports indexed documents missing from Chroma, chunks without document lineage, chunks for unknown documents, chunks for known but non-expected documents, and subject mismatches. Drift is reported with a nonzero exit code; automated repair is not yet implemented.

The core application lifecycle remains covered by `tests/test_document_lifecycle_e2e.py`, which exercises real FastAPI routes, repositories, lifecycle orchestration, format-aware source metadata, and an isolated temporary Chroma index. Deterministic test doubles replace external embedding and answer generation at that boundary, while focused contract, loader, chunker, repository, service, API, and CLI tests cover PDF/TXT/DOCX validation, citation lineage, duplicate handling, retry, deletion, rebuild, stale recovery, subject trash and restore, legacy-source repair, and reconciliation reporting.

A live local recovery was verified on 2026-10-17 against the application state merged through PR #26. A legacy BigData document retained its original `document_id`, received verified source metadata, restored its subject to `ACTIVE`, reached `INDEXED`, rebuilt 12 subject-scoped Chroma chunks, and produced a RAG answer citing `BigData_Lec06.pdf` pages 3, 4, and 6.

## Capability matrix

| Area | Status | Evidence or boundary |
| --- | --- | --- |
| Subject creation and active listing | Implemented | API, repository, and frontend verification |
| Subject trash and restore lifecycle | Implemented and automatically covered | Lifecycle states, failure recording, Chroma removal, retained-source rebuild, API tests, service tests, and live UI verification |
| PDF, TXT, and DOCX validation and upload | Implemented | Upload API tests cover extension, media type, content validity, empty input, filename, and size boundaries; TXT requires UTF-8 and non-empty DOCX tables are rejected |
| Canonical source metadata and storage boundary | Partially abstracted, implemented locally | PostgreSQL records `source_uri`, `content_sha256`, and `file_size_bytes`; uploads and retained-source validation use injected storage, while extraction still expects a local path and `LocalSourceStorage` remains the only implementation |
| Format-aware extraction and cleaning | Implemented | PDF pages, TXT lines, and DOCX body paragraphs retain their source boundaries through transform tests; DOCX manual line breaks are normalized inside their owning paragraph |
| Source-location contract | Implemented | `Document`, `Chunk`, Chroma metadata, chat schemas, and frontend rendering require exactly one of page, line range, or paragraph range |
| Overlapping chunk generation | Implemented | Chunk boundaries, overlap, indices, and page/line/paragraph metadata are automatically covered |
| PostgreSQL document lifecycle | Implemented | `UPLOADED`, `PROCESSING`, `INDEXED`, `FAILED`, and `DELETED` states plus processing attempts, heartbeat, and stage metadata |
| Duplicate-safe ingestion and failed retry | Implemented for sequential requests | Active duplicates are rejected; failed ingestion retries reuse retained source and document identity; concurrent-request uniqueness is not yet enforced |
| Stale-ingestion recovery | Implemented operator workflow | Stale selection, processing heartbeat, dry-run/apply CLI, failure handling, and automated tests |
| Subject metadata propagation | Implemented | Metadata flows through document, chunk, vector, retrieval, and chat layers |
| Subject-scoped retrieval | Implemented | Retriever and chat orchestration tests plus live local verification |
| Answer and source rendering | Implemented | Frontend renders context-constrained answers with document plus page, line-range, or paragraph-range references |
| Document deletion | Implemented and automatically covered | PDF, TXT, and DOCX lifecycle tests verify Chroma removal, PostgreSQL `DELETED` state, and post-delete retrieval behavior |
| Retained-source Chroma rebuild | Implemented through subject restore | Automated multi-format rebuild tests, the earlier 12-chunk PDF recovery, and live TXT trash/restore cycles preserve source identity and lineage; the latest cycle also verified retained-source hash, size, and cross-store identity |
| Guarded legacy-source repair | Implemented operator workflow | Dry-run-first CLI, checksum and size verification, conflict protection, idempotent rerun tests, and live recovery evidence |
| Legacy `subject_id` backfill | Completed locally | Dry run found 223 missing values; apply updated them; second dry run found 0 |
| Cross-store reconciliation audit | Implemented operator workflow | Dry-run reporting classifies missing indexed documents, missing lineage, unknown documents, known non-expected documents, and subject mismatches; repair remains manual |
| Retrieval and answer benchmark | Not implemented | No measured relevance, citation-correctness, or faithfulness baseline |
| Production operations | Not implemented | Authentication, authorization, monitoring, durable object storage, and deployment remain out of scope |

## Verification evidence

### Automated

- The full backend suite passed locally against `main` at `e0d6afbef4fce5beef0b8008d144da5f843d6324` with `245 passed` and one existing Starlette `TestClient` dependency deprecation warning.
- Frontend ESLint and the TypeScript/Vite production build passed locally with 180 modules transformed.
- `tests/test_document_lifecycle_e2e.py` covers PDF, TXT, and DOCX subject creation, upload, `INDEXED` state, subject-scoped retrieval with format-aware source lineage, deletion, PostgreSQL lifecycle state, Chroma removal, repeated upload behavior, failed-document retry, and retained-source rebuild.
- The lifecycle test uses SQLite in memory, an isolated temporary Chroma directory, real TXT reading and DOCX paragraph parsing, and deterministic substitutes for heavyweight PDF extraction, embedding, and answer generation.
- Contract, loader, cleaner, chunker, repository, storage, service, API, and CLI tests cover source-location validation, UTF-8 TXT lines, DOCX paragraph boundaries and manual line breaks, the explicit DOCX table rejection policy, canonical source metadata, local source-storage conflict and read behavior, injected retained-source validation, sequential duplicate protection, retained-source retry, processing heartbeats, stale-ingestion recovery, subject trash and restore, guarded legacy-source repair, and PostgreSQL-Chroma reconciliation reporting.
- Legacy-source repair tests cover dry run, explicit apply, source changes after planning, conflicting target files, conflicting PostgreSQL metadata, missing documents, and idempotent reruns.
- GitHub Actions backend and frontend checks passed through PR #30, including the multi-format ingestion and local source-storage boundary changes.
- CI does not run live PostgreSQL, Chroma, embedding, and Gemini together as one external integration workflow.

### Manual local end-to-end

Verified on 2026-10-19 against `main` at `e0d6afbef4fce5beef0b8008d144da5f843d6324`:

- Created subject `7bc902ef-1388-4db6-bb93-a0d3b3b84de9` and uploaded the UTF-8 TXT fixture `phase2-recovery-evidence.txt`.
- The upload created document `e53423ba-4577-4cc4-8b50-d8cdecfa9e07`, reached `INDEXED`, and produced one Chroma chunk with source line range 1-3.
- A live subject-scoped question returned an answer citing the same document identity and line range.
- Moving the subject to Trash changed it to `DELETED`, processed one document, removed one Chroma chunk, and caused chat to return `409 Subject is not active`.
- Restoring the subject returned it to `ACTIVE`, processed one retained document, and rebuilt one Chroma chunk.
- The post-restore query returned an answer with the same `document_id` and line range 1-3.
- A direct cross-store check confirmed `document_status=INDEXED`, no active processing stage, matching retained-source SHA-256 and file size, and exactly one Chroma chunk scoped to the expected subject.

Result: **passed**.

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

Verified on 2026-10-19 against `feat/txt-docx-ingestion` at `2564cbdbf10838c20f266cb82ca0153d0cb889ca`:

- Uploaded a real DOCX containing manual line breaks inside Word paragraphs. The first processing attempt exposed a source-boundary mismatch at the chunk stage; a focused regression test reproduced it, and extraction now normalizes internal line breaks without changing the paragraph count.
- Retried the retained DOCX with the original `document_id` `80a0ce09-ed1b-4955-9995-7ba6f9457525`, reached `INDEXED`, rebuilt 10 Chroma chunks, and returned a live answer citing paragraph ranges 8-19 and 16-28.
- Re-uploading the indexed DOCX was rejected with `409 DOCUMENT_ALREADY_EXISTS`, and the frontend rendered a user-facing already-indexed message.
- Uploaded `warehouse-lineage.txt`, received a live answer citing lines 1-3, moved its subject to Trash, verified PostgreSQL `DELETED` plus zero subject chunks in Chroma, restored the same document identity, rebuilt one chunk with line range 1-3, and received the same subject-scoped answer after restore.
- Asked the same warehouse question under the BigData subject and the TXT subject. Retrieval remained scoped: BigData returned PDF page references, while the TXT subject returned only the TXT line reference.

Result: **passed**.

## Data ownership boundary

| Data | Current owner | Current limitation |
| --- | --- | --- |
| Subject and document metadata | PostgreSQL | No production backup or restore procedure yet |
| Document and subject lifecycle state | PostgreSQL | Recovery workflows are operator-invoked rather than scheduled |
| Accepted PDF, TXT, and DOCX sources | `LocalSourceStorage`-backed canonical upload storage | Storage writes and retained-source reads have an interface boundary, but extraction still expects local paths and the files are not durable across machine or disk loss |
| Chunk vectors and retrieval metadata | Chroma | Derived and rebuildable when retained source metadata is complete; reconciliation detects drift but does not repair it automatically |
| Generated answers | API response | Not treated as a durable application record |

PostgreSQL is the system of record for identity, metadata, and lifecycle state. Chroma is a derived retrieval index. Chroma can be audited against PostgreSQL and rebuilt through subject restore when a valid retained source exists. The storage boundary removes direct filesystem writes from the upload API and direct retained-source reads from lifecycle validation, but the current recovery guarantee remains local because extraction still consumes a filesystem path and canonical files remain on the application machine.

## Known limitations

- `LocalSourceStorage` is the only source-storage implementation. Upload and retained-source validation use the boundary, but extraction still treats `source_uri` as a local filesystem path, so remote object storage is not yet plug-compatible.
- Duplicate-safe behavior covers sequential requests and failed retries; concurrent-request uniqueness is not enforced at the database level.
- Stale-ingestion recovery and legacy-source repair require an operator to run a CLI or initiate restore.
- PostgreSQL-Chroma reconciliation detects and classifies drift but does not repair it automatically.
- Legacy documents without source metadata still require the operator to locate and supply the correct original source file.
- TXT input is limited to UTF-8. DOCX ingestion supports body paragraphs; non-empty tables are explicitly rejected, and headers, footers, text boxes, images, and other complex Word structures are not extracted.
- Retrieval relevance, citation correctness, and answer faithfulness are not benchmarked.
- CI does not run live PostgreSQL, Chroma, embedding, and Gemini as one integration workflow.
- Dedicated health and readiness endpoints are not implemented.
- Structured operational logging, metrics, tracing, and alerting are incomplete.
- Authentication, authorization, rate limiting, and production deployment are not implemented.

## Next milestone priorities

1. Complete path-independent source access so extraction and rebuild consume source bytes or controlled temporary materialization through the storage interface instead of treating `source_uri` as a local path.
2. Add MinIO as the second local source-storage implementation, using stable object keys and preserving URI, SHA-256, and file size in PostgreSQL.
3. Migrate existing local sources with a dry-run-first workflow, per-file hash comparison, MinIO read-back verification, and no local deletion before successful verification.
4. Prove Chroma rebuild from MinIO with the same document identity, including missing objects, hash mismatches, temporary MinIO unavailability, and idempotent reruns.
5. Add database-level protection for concurrent duplicate ingestion and schedule stale-ingestion recovery.
6. Add guarded PostgreSQL-Chroma repair actions on top of the existing reconciliation audit.
7. Create a small multi-format retrieval and answer-quality evaluation dataset with relevance, citation-correctness, and faithfulness checks.
8. Before private beta, establish independent PostgreSQL and source-file backups, test restoration from those backups, then add authentication and authorization.

## Update policy

Update this document when a milestone changes, a limitation is removed, or new verification evidence is produced. Every update should include:

- the snapshot date;
- the application commit or release being described;
- links or stable identifiers for reproducible CI or test evidence;
- capabilities added or removed;
- known limitations that changed;
- the next milestone priorities.

Use Git history, pull requests, and issues for chronological development activity. Do not turn this file into a running activity log.
