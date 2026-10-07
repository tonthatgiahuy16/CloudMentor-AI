# CloudMentor AI — Project Status

This document records the implementation status of CloudMentor AI at a specific point in Git history. It complements the public overview in [`README.md`](../README.md); it is not a daily development log or a replacement for issues and pull requests.

## Status snapshot

| Field | Value |
| --- | --- |
| Snapshot date | 2026-10-07 |
| Application baseline | [`89fd45d`](https://github.com/tonthatgiahuy16/CloudMentor-AI/commit/89fd45dda10212c866f7baaa4ea85d0b00e37e46) |
| Current milestone | Subject-scoped local RAG vertical slice |
| Overall state | Core workflow and manual local end-to-end scenario verified; automation, recovery, and evaluation hardening remain |
| CI evidence | [GitHub Actions run 37422895674](https://github.com/tonthatgiahuy16/CloudMentor-AI/actions/runs/37422895674) |

The status was captured against `main` at `89fd45d` before this update receives its own commit.

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

This complete sequence passed a manual local end-to-end test on 2026-10-07 against commit `89fd45d`. It has not yet been captured as an automated reproducible end-to-end test.

## Capability matrix

| Area | Status | Evidence or boundary |
| --- | --- | --- |
| Subject creation and listing | Implemented | API and repository tests; manual frontend smoke test |
| PDF validation and upload | Implemented | Upload API tests cover type, signature, filename, and size boundaries |
| Page-level extraction and cleaning | Implemented | Loader and transformation tests |
| Overlapping chunk generation | Implemented | Chunk boundaries, overlap, indices, and metadata tests |
| Embedding and Chroma indexing | Implemented locally | External embedding and live Chroma boundaries are not covered as one CI integration test |
| PostgreSQL document lifecycle | Implemented | `UPLOADED`, `PROCESSING`, `INDEXED`, and `FAILED` states |
| Subject metadata propagation | Implemented | Metadata flows through document, chunk, vector, retrieval, and chat layers |
| Subject-scoped retrieval | Implemented | Retriever and chat orchestration tests; manual smoke test |
| Answer and source rendering | Implemented | Frontend renders context-constrained answers with document/page references |
| Document deletion | Implemented and manually verified end-to-end | Covered by service/API tests; after deletion, the repeated question no longer retrieved the deleted document in the verified manual workflow |
| Legacy `subject_id` backfill | Completed locally | Dry run found 223 missing values; apply updated them; second dry run found 0 |
| Automated Chroma rebuild | Not implemented | Recovery roadmap item |
| Cross-store reconciliation | Not implemented | PostgreSQL-Chroma consistency roadmap item |
| Retrieval and answer benchmark | Not implemented | No measured relevance, citation-correctness, or faithfulness baseline |
| Production operations | Not implemented | Authentication, authorization, monitoring, and deployment remain out of scope |

## Verification evidence

### Automated

- GitHub Actions completed successfully for application baseline `89fd45d` on 2026-10-06.
- `unit-tests` passed for the current 58-test backend suite.
- `frontend-checks` passed, including ESLint and the Vite production build.
- The same frontend lint and production build were also run successfully on the local workspace.

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

The legacy Chroma metadata migration was also verified separately with dry run, apply, and a no-op second dry run. The manual end-to-end sequence should become an automated test before the project claims a fully reproducible vertical slice.

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

1. Automate the verified manual end-to-end scenario for the complete local document lifecycle.
2. Define durable canonical content storage and record URI/checksum metadata.
3. Make ingestion idempotent across retries and partial failures.
4. Implement Chroma rebuild and PostgreSQL-Chroma reconciliation workflows.
5. Create a small retrieval and answer-quality evaluation dataset.
6. Add health checks and structured operational diagnostics.

## Update policy

Update this document when a milestone changes, a limitation is removed, or new verification evidence is produced. Every update should include:

- the snapshot date;
- the application commit or release being described;
- links to reproducible CI or test evidence;
- capabilities added or removed;
- known limitations that changed;
- the next milestone priorities.

Use Git history, pull requests, and issues for chronological development activity. Do not turn this file into a running activity log.
