# CloudMentor AI — Project Status

This document records the implementation status of CloudMentor AI at a specific point in Git history. It complements the public overview in [`README.md`](../README.md); it is not a daily development log or a replacement for issues and pull requests.

## Status snapshot

| Field | Value |
| --- | --- |
| Snapshot date | 2026-10-27 |
| Application baseline | `5ffbe2912eac12a9687cb8f323fe7ac04b589f2d` |
| Current milestone | Phase 2.5 reliability evidence collected; F01 and F02 remain open |
| Overall state | PDF, UTF-8 TXT, and body-paragraph DOCX share a path-independent storage and extraction contract; PostgreSQL remains the system of record and Chroma remains a rebuildable derived index. Versioned retrieval and answer-level evaluation baselines validate source fixtures, evidence coverage, human-reviewed answer correctness and faithfulness, and refusal behavior across TXT, DOCX, and PDF, including distractors. A local Phase 2.5 run exercised ingestion, validation, duplicate protection, retry, lifecycle recovery, reconciliation, controlled repair, and stale recovery; it also found non-stable chunk IDs across rebuild and pre-existing local Chroma drift. |
| CI evidence | GitHub Actions backend, frontend, container-backed MinIO recovery, and PostgreSQL concurrent-ingestion checks passed through PRs #39 and #41; feature commit `f67f448` was locally verified with 320 backend tests passing, 3 skipped, and one existing Starlette `TestClient` dependency deprecation warning. |

This status reflects the application baseline at `5ffbe2912eac12a9687cb8f323fe7ac04b589f2d`. The Phase 2.5 local evidence run is documented in [`PHASE2_RELIABILITY_MANIFEST.md`](./PHASE2_RELIABILITY_MANIFEST.md) and [`PHASE2_RELIABILITY_REPORT.md`](./PHASE2_RELIABILITY_REPORT.md); it does not establish production readiness or authorize a private beta.

## Current capability

CloudMentor AI currently supports this local workflow:

```text
create subject
    -> validate and retain a canonical PDF, UTF-8 TXT, or body-paragraph DOCX through the configured source-storage adapter
    -> record source URI, SHA-256, and file size in PostgreSQL
    -> reject an active duplicate or retry a failed ingestion with the same identity
    -> read source bytes through storage, then extract, clean, and preserve page, line, or paragraph boundaries
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

Canonical source writes and reads use one injected `SourceStorage` contract. `LocalSourceStorage` and `MinioSourceStorage` implement that contract, while a shared factory selects the adapter for upload, subject restore, and stale-ingestion recovery. Extraction receives source bytes plus filename and type rather than treating `source_uri` as a filesystem path. A separate dry-run-first operator workflow migrates eligible local sources to deterministic MinIO objects, verifies their metadata and read-back bytes, and conditionally updates PostgreSQL without deleting the retained local copies.

A PostgreSQL-Chroma reconciliation workflow compares the relational lifecycle registry with the derived vector index. The default command is audit-only; `--repair` prints a dry-run plan, and `--repair --apply` explicitly deletes orphan chunks and rebuilds `INDEXED` documents that have no Chroma chunks. Planned, applied, and failed actions are logged, failures return a nonzero exit code, and independent actions continue after a failure. Chunks without lineage, chunks for known non-expected documents, and subject mismatches remain report-only.

The core application lifecycle remains covered by `tests/test_document_lifecycle_e2e.py`, which exercises real FastAPI routes, repositories, lifecycle orchestration, format-aware source metadata, and an isolated temporary Chroma index. Deterministic test doubles replace external embedding and answer generation at that boundary, while focused contract, loader, chunker, repository, service, API, and CLI tests cover PDF/TXT/DOCX validation, citation lineage, duplicate handling, retry, deletion, rebuild, stale recovery, subject trash and restore, legacy-source repair, and reconciliation reporting.

A live local recovery was verified on 2026-10-17 against the application state merged through PR #26. A legacy BigData document retained its original `document_id`, received verified source metadata, restored its subject to `ACTIVE`, reached `INDEXED`, rebuilt 12 subject-scoped Chroma chunks, and produced a RAG answer citing `BigData_Lec06.pdf` pages 3, 4, and 6.

## Capability matrix

| Area | Status | Evidence or boundary |
| --- | --- | --- |
| Subject creation and active listing | Implemented | API, repository, and frontend verification |
| Subject trash and restore lifecycle | Implemented and automatically covered | Lifecycle states, failure recording, Chroma removal, retained-source rebuild, API tests, service tests, and live UI verification |
| PDF, TXT, and DOCX validation and upload | Implemented | Upload API tests cover extension, media type, content validity, empty input, filename, and size boundaries; TXT requires UTF-8 and non-empty DOCX tables are rejected |
| Canonical source metadata and storage boundary | Implemented locally with two adapters | PostgreSQL records `source_uri`, `content_sha256`, and `file_size_bytes`; local-filesystem and MinIO adapters share one contract and factory; extraction, retry, stale recovery, and restore consume bytes through the selected adapter |
| Controlled local-to-MinIO source migration | Implemented operator workflow | Dry run is the default; apply validates local SHA-256 and size, writes a deterministic MinIO object, verifies read-back bytes, and conditionally replaces the PostgreSQL URI; reruns are safe and local copies are retained |
| MinIO recovery failure handling | Implemented and automatically covered | Missing objects and checksum mismatches mark the document failed before derived-vector deletion; temporary S3, connection, and stream-read failures become `SourceUnavailableError`, leave the document unchanged, and can be retried through subject restore |
| Format-aware extraction and cleaning | Implemented | PDF pages, TXT lines, and DOCX body paragraphs retain their source boundaries through transform tests; DOCX manual line breaks are normalized inside their owning paragraph |
| Source-location contract | Implemented | `Document`, `Chunk`, Chroma metadata, chat schemas, and frontend rendering require exactly one of page, line range, or paragraph range |
| Overlapping chunk generation | Implemented | Chunk boundaries, overlap, indices, and page/line/paragraph metadata are automatically covered |
| PostgreSQL document lifecycle | Implemented | `UPLOADED`, `PROCESSING`, `INDEXED`, `FAILED`, and `DELETED` states plus processing attempts, heartbeat, and stage metadata |
| Duplicate-safe ingestion and failed retry | Implemented with database concurrency protection | A partial unique PostgreSQL index rejects concurrent active documents with the same subject and content SHA-256; a reservation is created before source storage writes, while failed retries reuse retained source and document identity |
| Stale-ingestion recovery | Implemented operator workflow | Stale selection, processing heartbeat, dry-run/apply CLI, failure handling, and automated tests |
| Subject metadata propagation | Implemented | Metadata flows through document, chunk, vector, retrieval, and chat layers |
| Subject-scoped retrieval | Implemented | Retriever and chat orchestration tests plus live local verification |
| Answer and source rendering | Implemented | Frontend renders context-constrained answers with document plus page, line-range, or paragraph-range references |
| Document deletion | Implemented and automatically covered | PDF, TXT, and DOCX lifecycle tests verify Chroma removal, PostgreSQL `DELETED` state, and post-delete retrieval behavior |
| Retained-source Chroma rebuild | Implemented through subject restore | Automated multi-format and failure-path rebuild tests plus live local-filesystem and MinIO cycles preserve source identity and lineage; the MinIO cycle rebuilt 14 TXT/DOCX/PDF chunks and preserved format-aware citations, and a live outage retry rebuilt the same document without duplicate vectors |
| Guarded legacy-source repair | Implemented operator workflow | Dry-run-first CLI, checksum and size verification, conflict protection, idempotent rerun tests, and live recovery evidence |
| Legacy `subject_id` backfill | Completed locally | Dry run found 223 missing values; apply updated them; second dry run found 0 |
| Controlled PostgreSQL-Chroma reconciliation repair | Implemented operator workflow | Default audit and `--repair` are dry runs; `--repair --apply` deletes orphan chunks and rebuilds active indexed documents with no chunks, logs each outcome, isolates per-action failure, and is safe to rerun; missing lineage, known non-expected documents, and subject mismatches remain report-only |
| Retrieval-evaluation baseline | Implemented locally | A versioned four-case TXT/DOCX/PDF dataset, three distractors, fixture/evidence validation, evidence-coverage scoring, a CLI, and automated tests. Manual subject-scoped retrieval returned expected evidence for 3/3 answerable cases; the unanswerable case still returned context. |
| Answer-quality and faithfulness baseline | Implemented locally | Human-reviewed answer correctness, faithfulness, and refusal labels are combined with automated citation-coverage scoring from source lineage. A CLI aggregates the results; the narrow live baseline scored 3/3 answerable cases and 1/1 appropriate refusal. |
| Production operations | Not implemented | A local MinIO adapter exists, but independent backups, authentication, authorization, monitoring, and deployment remain out of scope |

## Verification evidence

### Automated

- The full backend suite passed locally against retrieval-evaluation feature commit `061224df9259d4d96c7c2a14546789ee3b86b5c1` with `313 passed, 3 skipped` and one existing Starlette `TestClient` dependency deprecation warning. The local run used a project-local pytest temporary directory because the default Windows pytest temp root was inaccessible.
- The full backend suite passed locally against answer-evaluation feature commit `f67f448` with `320 passed, 3 skipped` and the same existing warning. This run also used a project-local pytest temporary directory.
- Frontend ESLint and the TypeScript/Vite production build passed locally with 180 modules transformed.
- `tests/test_document_lifecycle_e2e.py` covers PDF, TXT, and DOCX subject creation, upload, `INDEXED` state, subject-scoped retrieval with format-aware source lineage, deletion, PostgreSQL lifecycle state, Chroma removal, repeated upload behavior, failed-document retry, and retained-source rebuild.
- The lifecycle test uses SQLite in memory, an isolated temporary Chroma directory, real TXT reading and DOCX paragraph parsing, and deterministic substitutes for heavyweight PDF extraction, embedding, and answer generation.
- Contract, loader, cleaner, chunker, repository, storage, service, API, and CLI tests cover source-location validation, UTF-8 TXT lines, DOCX paragraph boundaries and manual line breaks, the explicit DOCX table rejection policy, canonical source metadata, local and MinIO source-storage contracts, storage-factory selection, injected retained-source validation, controlled local-to-MinIO migration, concurrent duplicate protection, retained-source retry, processing heartbeats, stale-ingestion recovery, subject trash and restore, guarded legacy-source repair, and PostgreSQL-Chroma reconciliation audit and repair.
- MinIO hardening tests classify missing-object errors separately from temporary S3, connection, and stream-read failures; responses are released after stream failures. Rebuild tests verify that missing sources and checksum mismatches fail before derived-vector deletion, while a temporary source outage leaves the document unchanged and allows a later restore retry.
- Legacy-source repair tests cover dry run, explicit apply, source changes after planning, conflicting target files, conflicting PostgreSQL metadata, missing documents, and idempotent reruns.
- Local-to-MinIO migration tests cover dry-run classification, explicit apply, stale PostgreSQL snapshots, local-source changes, failed object read-back, commit rollback, per-document failure isolation, Unicode output on limited Windows consoles, and idempotent reruns.
- GitHub Actions passed backend and frontend checks through PR #37. It also runs a pinned container-backed MinIO recovery integration job and a PostgreSQL concurrent-ingestion integration job.
- CI still does not run live PostgreSQL, Chroma, embedding, and Gemini together as one external integration workflow.

### Manual local end-to-end

Verified on 2026-10-26 on `feat/rag-evaluation-baseline`; the evaluated changes were subsequently committed as `061224df9259d4d96c7c2a14546789ee3b86b5c1`:

- Created isolated evaluation subjects and uploaded one original fixture plus one distractor for each TXT, DOCX, and PDF source.
- Queried the real embedding service and subject-scoped retriever without calling Gemini.
- All 3 answerable cases returned evidence covering the expected source location.
- The unanswerable backup-schedule case returned two contexts, including the storage distractor as the nearest result.
- `python -m evaluation.run_retrieval_score` reported `answerable_case_count=3`, `retrieval_hits=3`, `retrieval_hit_rate=1.0`, `unanswerable_case_count=1`, and `unanswerable_cases_with_results=1`.

Result: **passed for the narrow retrieval-evidence baseline**. This verification did not evaluate generated answers, citation correctness at answer level, faithfulness, or refusal behavior.

Verified on 2026-10-27 on `feat/rag-answer-evaluation`; the evaluated changes were subsequently committed as `f67f448`:

- Used the isolated TXT, DOCX, and PDF evaluation subjects and their original fixtures plus distractors.
- Called the real `/chat/` endpoint and Gemini answer generator for all four cases, preserving the returned source locations in local observations.
- Human review marked all 3 answerable responses correct and faithful; automated lineage scoring found expected citation coverage for all 3.
- The unanswerable backup-schedule case retrieved two contexts but responded with an appropriate refusal; human review marked `refusal_correct=true`.
- `python -m evaluation.run_answer_score` reported `answerable_case_count=3`, `answer_correct_count=3`, `citation_hit_count=3`, `faithful_count=3`, `unanswerable_case_count=1`, and `refusal_correct_count=1`, with each rate equal to `1.0` on this narrow dataset.

Result: **passed for the narrow answer-level baseline**. Correctness, faithfulness, and refusal are human-reviewed labels; this result does not establish broad model quality or production readiness.

Verified on 2026-10-21 against `feat/controlled-reconciliation-repair` at `f263589829661ef1e0a7304c5a4e3922573b9773`:

- `python -m scripts.reconcile_postgres_chroma --repair` returned `repair_mode=dry-run` and `Repair plan is empty.`; it made no change.
- `python -m scripts.reconcile_postgres_chroma --repair --apply` returned `deleted_orphan_chunks=0`, `rebuilt_documents=0`, `rebuilt_chunks=0`, and `failed_actions=0` for that empty plan.
- Mutation paths are covered by focused regression tests: orphan deletion, rebuild of an indexed document with no vectors, action-level failure isolation, logged failure output, nonzero failure exit status, and idempotent rerun after repair.

Result: **passed for the no-drift local state**. This manual run did not create artificial drift; the apply mutation paths are verified by automated tests.

Verified on 2026-10-20 against `feat/minio-recovery-hardening` at `0d82db5aa93f24014cf1e93a5e32247fff0d776f`:

- Created subject `72f237ea-b136-4b87-9e1c-6c1a2e9c73e0` and MinIO-backed document `45893fd7-e09f-484e-b996-d1449041e4d1`. PostgreSQL recorded its stable `minio://cloudmentor-sources/documents/{document_id}/source.txt` URI, SHA-256, size, and `INDEXED` status.
- Moving the subject to Trash removed its one derived Chroma chunk. With MinIO stopped, restore returned an API failure; direct state inspection showed `RESTORE_FAILED` with `Source storage is temporarily unavailable`, while the document remained `INDEXED` under the same source URI and Chroma had zero chunks.
- After MinIO was restarted and its live endpoint returned `200`, restore returned the subject to `ACTIVE`, processed one document, and rebuilt one Chroma chunk under the unchanged document ID. A second restore returned `200` with `processed_documents=0` and `indexed_chunks=0`, demonstrating an idempotent no-op after recovery.

Result: **passed**.

Verified on 2026-10-20 against `feat/migrate-local-sources-to-minio` at `0861decd5d691f4125bb5f85758210d0ac5b82f6`:

- The initial inventory classified eight eligible local sources, three existing MinIO sources, and ten legacy document rows with incomplete source metadata.
- Dry run validated every eligible local source against the SHA-256 and file size stored in PostgreSQL without writing objects or changing document state.
- The first apply migrated five documents and reported three failures caused by Unicode filenames reaching a limited Windows console. The successfully migrated documents remained valid, the three failed rows stayed on their original local URIs, and the command returned a nonzero exit code.
- After adding Unicode-safe operator output and regression coverage, a resumed dry run found exactly the three remaining eligible documents. Apply migrated all three, and the final dry run was a no-op with zero eligible documents, eleven already-MinIO documents, and zero failures.
- Post-migration verification read all eleven MinIO objects and confirmed `11/11` SHA-256 and size matches against PostgreSQL.
- All eight migrated local source files were deliberately retained. The ten rows with incomplete source metadata were not modified, and migration did not delete or rebuild Chroma data.

Result: **passed**.

Verified on 2026-10-19 against `feat/minio-source-storage` at `553544c8d9dd912085d3f7f931fb2331f2900a71`:

- Started a real local MinIO service, provisioned bucket `cloudmentor-sources`, and confirmed its live health endpoint.
- Created subject `98179032-ca3a-489e-bad1-eb4edc56f19f` and uploaded a UTF-8 TXT, body-paragraph DOCX, and PDF as new documents.
- PostgreSQL stored stable `minio://cloudmentor-sources/documents/{document_id}/source.{extension}` URIs, SHA-256 values, and file sizes for all three documents; no matching canonical files existed under `storage/uploads`.
- The documents reached `INDEXED` with 1 TXT chunk, 1 DOCX chunk, and 12 PDF chunks. Live questions returned the expected source identities with TXT lines 1-3, DOCX paragraphs 1-3, and PDF pages 3 and 4.
- Moving the subject to Trash processed three documents and removed all 14 subject-scoped Chroma chunks.
- Restoring the subject read the retained MinIO objects, returned the subject to `ACTIVE`, processed the same three documents, and rebuilt all 14 Chroma chunks.
- Post-restore questions preserved document IDs `a1fac31a-cd26-4883-8f5a-32d8ea941e9e`, `ceb1572f-1730-47be-9acc-d0678f81667a`, and `0ff5816f-5eae-4714-8ffd-b8ba48059122`, together with their line, paragraph, and page citations.
- Direct adapter reads returned 165, 36,673, and 1,061,675 bytes respectively; every read matched the SHA-256 and file size recorded in PostgreSQL.

Result: **passed**.

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
| Accepted PDF, TXT, and DOCX sources | Configured `LocalSourceStorage` or `MinioSourceStorage` | Both adapters support path-independent reads for retry and rebuild; all eight eligible local sources were migrated and verified while their local copies were retained; ten legacy rows still lack complete source metadata, and the verified MinIO service has no independent backup yet |
| Chunk vectors and retrieval metadata | Chroma | Derived and rebuildable when retained source metadata is complete; reconciliation has bounded operator repair for orphan chunks and indexed documents with no chunks, but current rebuilds regenerate chunk IDs |
| Generated answers | API response | Not treated as a durable application record |

PostgreSQL is the system of record for identity, metadata, and lifecycle state. Chroma is a derived retrieval index. Chroma can be audited against PostgreSQL and rebuilt through subject restore when a valid retained source exists. The storage boundary removes filesystem assumptions from extraction and lifecycle recovery, while the current MinIO guarantee remains local because the service and its volume are not independently backed up or operated as production infrastructure.

## Known limitations

- The controlled migration covered all eight eligible local sources, but ten legacy document rows still lack the complete retained-source metadata required for automatic migration.
- The verified MinIO service and volume are local; independent source-file and PostgreSQL backup and restore procedures are not established.
- Automated storage and service tests cover missing MinIO objects, changed bytes, temporary S3 failures, connection failures, and interrupted reads. A temporary outage and successful retry were also verified with live local MinIO; live missing-object and changed-object exercises remain unrecorded.
- MinIO recovery has container-backed CI coverage, but the deployed local MinIO service remains manually operated.
- Concurrent duplicate protection is implemented at the PostgreSQL boundary; production throughput, timeout, and contention behavior is not yet benchmarked.
- Stale-ingestion recovery and legacy-source repair require an operator to run a CLI or initiate restore.
- Phase 2.5 evidence found that Chroma `chunk_id` values are regenerated during rebuild. Document identity and source lineage remain available, but stable chunk identity is not currently satisfied.
- PostgreSQL-Chroma reconciliation repair is intentionally bounded to orphan chunks and `INDEXED` documents with no chunks; missing lineage, known non-expected documents, and subject mismatches still require operator review.
- The local reconciliation audit found 83 chunks without `document_id` lineage and 254 chunks belonging to two known `FAILED` documents. These report-only categories remain unresolved and local stores must not be described as consistent.
- Legacy documents without source metadata still require the operator to locate and supply the correct original source file.
- TXT input is limited to UTF-8. DOCX ingestion supports body paragraphs; non-empty tables are explicitly rejected, and headers, footers, text boxes, images, and other complex Word structures are not extracted.
- A small retrieval and answer-level evaluation baseline exists, but it contains only four cases. Answer correctness, faithfulness, and refusal are human-reviewed; broader retrieval relevance and answer quality are not yet benchmarked.
- CI does not run live PostgreSQL, Chroma, embedding, and Gemini as one integration workflow.
- Dedicated health and readiness endpoints are not implemented.
- Structured operational logging, metrics, tracing, and alerting are incomplete.
- Authentication, authorization, rate limiting, and production deployment are not implemented.

## Next milestone priorities

1. Resolve the stable chunk-identity contract or explicitly revise it, then rerun the affected rebuild and recovery evidence.
2. Define a retention, review, and repair policy for the 83 missing-lineage chunks and the two known failed-document chunk sets before making a cross-store consistency claim.
3. Establish independent PostgreSQL and source-file backups, then test restoration from those backups before making a production-readiness claim.
4. Add metrics, structured logs, tracing, and health/readiness endpoints for ingestion, storage, and reconciliation operations.
5. Add authentication, authorization, and rate limiting before private beta.
6. Expand the multi-format retrieval and answer-level datasets with harder relevance, citation, faithfulness, and refusal cases.

## Update policy

Update this document when a milestone changes, a limitation is removed, or new verification evidence is produced. Every update should include:

- the snapshot date;
- the application commit or release being described;
- links or stable identifiers for reproducible CI or test evidence;
- capabilities added or removed;
- known limitations that changed;
- the next milestone priorities.

Use Git history, pull requests, and issues for chronological development activity. Do not turn this file into a running activity log.
