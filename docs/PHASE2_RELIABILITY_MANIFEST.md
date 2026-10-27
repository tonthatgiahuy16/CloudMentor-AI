# Phase 2.5 — Reliability Evidence Manifest

> Purpose: measure and demonstrate existing Phase 2 reliability mechanisms.
> This artifact does not add product functionality or authorize a private beta.

## Execution boundary

- Evidence branch: `docs/phase2-reliability-evidence`
- Application commit: record the commit at the start of execution
- Environment: local and isolated from day-to-day development data
- Source storage: record `local` or `minio`
- Test subjects: use the `phase25-evidence-YYYYMMDD` prefix
- Safety rule: do not run mutation commands against subjects or documents outside that prefix.

## Required measurements

Record the following for every case:

- start and end time, including duration;
- `subject_id`, `document_id`, and source format;
- document lifecycle status and Chroma chunk count;
- PostgreSQL–Chroma reconciliation result;
- command, observed output, and log artifact;
- final status: `passed`, `failed`, or `blocked`.

## Evidence cases

| Case ID | Purpose | Existing mechanism under test | Expected outcome |
| --- | --- | --- | --- |
| R01 | Ingest valid TXT, DOCX, and PDF files | Upload → extract → transform → chunk → index | Each document reaches `INDEXED` with valid source metadata and chunk lineage. |
| R02 | Reject invalid input | Validation boundary | Invalid input does not result in an `INDEXED` document or orphan vector. |
| R03 | Re-submit duplicate input | Concurrent duplicate protection | The operation does not create duplicate business effects or duplicate vectors. |
| R04 | Retry from retained source | Retained-source retry and rebuild | The retry preserves `document_id` and does not duplicate vectors. |
| R05 | Move a subject to Trash and restore it | Subject lifecycle service | Trash removes derived vectors; Restore rebuilds from canonical source while preserving lineage. |
| R06 | Audit PostgreSQL and Chroma consistency | `scripts.reconcile_postgres_chroma` | The report identifies missing, orphan, lineage, and subject-scope mismatches. |
| R07 | Detect and repair controlled drift | Reconciliation repair | An isolated environment detects drift; dry run lists actions; explicit apply restores the derived state. |
| R08 | Recover stale ingestion | `scripts.recover_stale_ingestions` | Dry run identifies candidates; apply recovers only the intended isolated document. |

## Explicit exclusions

- No permanent deletion of subjects or documents.
- No authentication, authorization, rate limiting, backup, monitoring, or deployment work.
- No production-readiness claim based on local results.
- No private data or non-evidence subjects.

## Completion gate

Phase 2.5 reliability evidence is complete only when:

1. R01–R08 have observed results or an explicitly documented `blocked` reason.
2. R07 is executed in an isolated environment and distinguishes dry run from apply.
3. A final report links the commit, manifest, logs, measurements, and known limitations.
4. `PROJECT_STATUS.md` is updated only after the evidence has been reviewed.
