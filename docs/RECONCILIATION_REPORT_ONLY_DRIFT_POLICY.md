# Reconciliation Report-Only Drift Policy

## Purpose

This policy governs PostgreSQL-Chroma drift classifications that the reconciliation workflow reports but does not repair automatically.

Its purpose is to preserve PostgreSQL as the system of record, prevent unreviewed loss of derived data, and make any manual Chroma cleanup reproducible and auditable.

This policy does not add application functionality, authorize permanent deletion, or establish production readiness.

## Scope

This policy applies only when `scripts.reconcile_postgres_chroma` reports a drift category without generating an existing bounded repair action.

Current examples include:

- chunks with missing lineage metadata;
- chunks for known non-expected documents;
- subject mismatches.

The existing reconciliation workflow remains responsible for its supported repair classes:

- deleting orphan derived chunks;
- rebuilding an `INDEXED` document that has no derived chunks.

## Safety rules

1. PostgreSQL remains the system of record.
2. Chroma remains a rebuildable derived index.
3. Never delete or modify PostgreSQL rows, subjects, or retained source files under this policy.
4. Never infer `document_id` or `subject_id` from a filename alone.
5. Never run a broad or wildcard Chroma deletion.
6. Never apply a report-only cleanup without a reviewed manifest of exact chunk IDs.
7. A dry run, snapshot, and post-apply audit are required for every cleanup.
8. If evidence is incomplete or classifications are ambiguous, stop and record the case as `blocked`.

## Required operator workflow

### 1. Audit

Run the default reconciliation command without mutation:

```powershell
python -m scripts.reconcile_postgres_chroma
```

Record:

- application commit;
- execution time and exit code;
- counts for every reported drift category;
- affected document IDs, subject IDs, source names, and chunk IDs where available.

### 2. Classify

Classify every affected chunk before proposing a change.

| Classification | Required review | Default decision |
| --- | --- | --- |
| Missing lineage | Determine whether a trustworthy PostgreSQL relationship exists through durable metadata, not filename matching | Block if no trustworthy relationship exists; otherwise prepare an explicit reviewed remediation plan |
| Known non-expected document | Confirm PostgreSQL lifecycle state, subject state, retained-source availability, and whether the vector is still derived from an intended active document | Do not rebuild a `FAILED` or deleted document automatically; consider exact derived-chunk cleanup only after review |
| Subject mismatch | Confirm the PostgreSQL subject ownership and retained source before any action | Block automatic cleanup or reassignment |
| Any ambiguous classification | Preserve all state and collect more evidence | Block |

### 3. Create a snapshot and manifest

Before any mutation:

1. Export every proposed target chunk record, including its exact `chunk_id`, metadata, and classification.
2. Record the snapshot path, SHA-256 checksum, creation time, application commit, and total target count.
3. Create a manifest that contains the exact IDs proposed for cleanup and the reason for every classification.
4. Do not include chunk text, credentials, or private source content in a committed manifest.

The operator must verify that:

- every snapshot ID exists in the live Chroma collection;
- the live target set exactly matches the reviewed manifest;
- no ID outside the manifest is eligible for mutation.

### 4. Review and approval

A cleanup requires explicit operator approval after reviewing:

- the reconciliation audit;
- the classification rationale;
- the snapshot checksum and count;
- the exact chunk-ID manifest;
- the intended mutation scope;
- the expected post-apply audit result.

For a solo project, the project owner performs and records this review. Approval does not permit a broader cleanup than the reviewed manifest.

### 5. Apply the exact approved action

Apply only the approved exact chunk IDs.

The action must:

- affect Chroma derived chunks only;
- log the number of deleted records;
- stop and report failure if the live target set no longer matches the reviewed manifest;
- avoid deletion by filename, subject name, wildcard, or unreviewed query.

### 6. Verify

Immediately run reconciliation again:

```powershell
python -m scripts.reconcile_postgres_chroma
```

Record:

- exit code and duration;
- all remaining drift counts;
- whether the intended targets are absent;
- whether unrelated drift changed unexpectedly.

If unexpected drift appears, stop further cleanup and record the result as `failed` or `blocked`.

## Evidence record

Each report-only drift decision must record:

| Field | Required value |
| --- | --- |
| Application commit | Exact Git commit used for the audit and action |
| Environment | Local, isolated, staging, or another named environment |
| Audit result | Command, exit code, duration, and reported counts |
| Classification | Per-category rationale and affected records |
| Snapshot | Path, SHA-256 checksum, and record count |
| Manifest | Exact target IDs and review status |
| Apply result | Exact action, deleted count, and failure details |
| Verification | Post-apply reconciliation result |
| Limitations | Unresolved categories, assumptions, and excluded records |

Material remediation evidence should be summarized in `PROJECT_STATUS.md` and linked from the relevant reliability report.

## Historical F02 example

The 2026-10-27 local F02 remediation provides a historical example that this policy formalizes:

- 337 derived chunks were snapshotted before cleanup;
- the snapshot was classified as 83 missing-lineage chunks and 254 chunks for two known `FAILED` documents;
- PostgreSQL rows, subjects, and retained source files were not deleted;
- the exact snapshot IDs were verified against live Chroma records;
- cleanup removed 337 of 337 target chunks;
- the post-cleanup reconciliation audit reported consistent stores.

This example is local evidence only. It does not authorize automatic cleanup of future report-only drift.