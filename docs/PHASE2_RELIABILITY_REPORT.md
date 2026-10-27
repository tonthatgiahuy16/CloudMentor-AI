# Phase 2.5 - Reliability Evidence Report

> This report records observed evidence for the Phase 2.5 reliability manifest.
> Local results do not establish production readiness.

## Execution baseline

| Field | Value |
| --- | --- |
| Evidence branch | `docs/phase2-reliability-evidence` |
| Application commit | `5ffbe2912eac12a9687cb8f323fe7ac04b589f2d` |
| Environment | Local isolated evidence run |
| Source storage | `local` (factory default) |
| Evidence subject | `phase25-evidence-20261027-r01` |
| Subject ID | `fb72ba03-a448-47e6-96ae-d1b1eb60a77d` |
| Run started | `2026-10-27T22:03:18.5211110+07:00` |

## R01 - Valid multi-format ingestion

**Status:** `passed`
**Evidence type:** Manual local execution
**Scope:** One isolated subject with self-created TXT, DOCX, and PDF fixtures.

| Format | Document ID | Lifecycle status | Upload-to-`INDEXED` latency | API end-to-end duration | Chroma chunks | Preserved source location |
| --- | --- | --- | ---: | ---: | ---: | --- |
| TXT | `4d4172b8-83e1-4ece-b678-387504916c27` | `INDEXED` | 1.109 s | 13.710 s | 1 | Lines 1-3 |
| DOCX | `91b6dc3c-21a1-4138-9e30-a5f61c19bc1b` | `INDEXED` | 2.732 s | 7.903 s | 1 | Paragraphs 1-3 |
| PDF | `9edd3053-85a9-447a-8d27-290358ca1d5b` | `INDEXED` | 0.388 s | 5.568 s | 1 | Page 1 |

### Observed checks

- The `/documents/` read path reported all three documents under the isolated subject with `status=INDEXED`.
- Direct Chroma metadata inspection found one chunk per document.
- Each chunk retained the isolated `subject_id`, its `document_id`, the expected source filename, and one valid format-specific source location.
- No document outside the evidence subject was mutated by this case.

### Limitations

- This case measures one small fixture per supported format; it does not establish throughput, large-file performance, or broad extraction quality.
- The report relies on post-upload lifecycle and Chroma checks. The upload HTTP response codes were not retained as a separate artifact.

## R02 - Invalid input rejection

**Status:** `passed`
**Evidence type:** Manual local execution
**Input:** An empty UTF-8 TXT file submitted to the isolated R01 subject.

| Check | Observed result |
| --- | --- |
| API response | `HTTP 400` |
| Validation message | `TXT file is empty` |
| API end-to-end duration | 4.017 s |
| Documents after rejection | 3; unchanged from R01 |
| Chroma chunks after rejection | 3; unchanged from R01 |

### Observed checks

- The upload request was rejected at the validation boundary.
- The isolated subject retained only the three R01 documents.
- Chroma retained only the three R01 chunks; the rejected input produced no derived vector.

### Limitations

- This case covers an empty TXT file only. Unsupported extensions, malformed PDF files, malformed DOCX files, and oversized files are not yet manually exercised in this evidence run.

## R03 - Duplicate upload protection

**Status:** `passed`
**Evidence type:** Manual local execution
**Input:** The already indexed `storage_basics.txt` fixture was uploaded again to the same isolated subject.

| Check | Observed result |
| --- | --- |
| API response | `HTTP 409` |
| Error code | `DOCUMENT_ALREADY_EXISTS` |
| Returned document ID | `4d4172b8-83e1-4ece-b678-387504916c27` |
| Returned lifecycle status | `INDEXED` |
| API end-to-end duration | 4.353 s |
| Document count after duplicate request | 3; unchanged |
| Chroma chunk count after duplicate request | 3; unchanged |
| Document IDs unchanged | `true` |
| Chunk IDs unchanged | `true` |

### Observed checks

- The duplicate request was rejected rather than creating another active document.
- The API identified the original document by its existing `document_id`.
- PostgreSQL document identity and Chroma chunk identity remained unchanged after the rejected request.

### Limitations

- This case covers a repeated upload in one local process and one subject. It does not measure concurrent upload contention or distributed retry behavior.

## R04 - Retry from retained source

**Status:** `passed`
**Evidence type:** Automated isolated lifecycle tests
**Command:** Focused retry tests with a project-local pytest temporary directory.

| Check | Observed result |
| --- | --- |
| PDF failed-document retry | Passed |
| TXT failed-document retry | Passed |
| DOCX failed-document retry | Passed |
| Test result | `3 passed, 1 warning in 2.34s` |

### Observed checks

- Each test creates an isolated failed document, retries from its retained source, and verifies that the original document identity is reused.
- The tested retry paths cover PDF, TXT, and DOCX inputs.
- The test suite verifies that retry does not leave duplicate derived vectors.

### Limitations

- These are isolated automated tests with temporary dependencies. They do not substitute for a live source-storage outage and recovery exercise.

## R05 - Subject Trash and Restore

**Status:** `passed`
**Evidence type:** Manual local execution
**Scope:** The isolated R01 subject and its three evidence documents.

| Action | HTTP status | Lifecycle result | Documents processed | Derived chunks | Duration |
| --- | ---: | --- | ---: | ---: | ---: |
| Trash | 200 | `DELETED` | 3 | 3 deleted | 0.246 s |
| Restore | 200 | `ACTIVE` | 3 | 3 indexed | 5.585 s |

### Observed checks

- After Trash, the subject appeared in `/subjects/trash` with `status=DELETED`, no documents were visible through `/documents/`, and Chroma contained zero chunks for the subject.
- After Restore, all three original document IDs were visible again and Chroma contained three rebuilt chunks.
- Restored chunk lineage preserved the source filename and format-specific source location: TXT lines 1-3, DOCX paragraphs 1-3, and PDF page 1.

### Historical finding F01 - Chunk IDs were not stable across rebuild

- Before Trash, the evidence subject had three Chroma chunk IDs.
- After Restore, the subject again had three chunks, but none of the previous chunk IDs was reused.
- At the time of this run, the chunker generated a new UUID on each chunking run.
- Therefore, document identity and source lineage were preserved, but stable chunk identity was not satisfied at the time of the original evidence run.

### Limitations

- This exercise uses one chunk per document. It does not establish that multi-chunk documents preserve stable chunk identity or deterministic chunk ordering after rebuild.

## R06 - PostgreSQL-Chroma reconciliation audit

**Status:** `failed`
**Evidence type:** Manual local audit
**Command:** `python -m scripts.reconcile_postgres_chroma`

| Check | Observed result |
| --- | ---: |
| Audit exit code | 1 |
| Audit duration | 1.840 s |
| Expected active indexed documents | 9 |
| Chroma chunks | 802 |
| Missing indexed documents | 0 |
| Missing lineage chunks | 83 |
| Unknown or orphan chunks | 0 |
| Known non-expected documents | 2 |
| Subject mismatches | 0 |

### Observed drift

- 83 Chroma chunks have no `document_id`, so they cannot be traced to a PostgreSQL document.
- Two `FAILED` documents under an active subject still have Chroma chunks: one has 131 chunks and the other has 123 chunks.
- No active indexed document was missing all of its Chroma chunks.
- No chunk had a mismatched `subject_id`.

### Interpretation

- The audit mechanism successfully detected and classified local drift.
- The local PostgreSQL-Chroma state is not consistent and must not be reported as reconciled.
- No repair mutation was run against this existing local drift.

## Findings

### F01 - Deterministic chunk identity

**Status:** Remediated with local runtime evidence on 2026-10-28

The original R05 Restore exercise generated new chunk IDs. PR #45 replaced random chunk IDs with versioned deterministic UUID v5 values derived from document identity, chunk position, source location, chunking configuration, and a SHA-256 hash of chunk text. Unit and pipeline coverage passed, followed by a separate isolated runtime Trash and Restore exercise that preserved all recorded chunk IDs, document IDs, and source lineage.

### F02 - Existing local Chroma drift

**Status:** Remediated locally after the evidence run
R06 found 83 chunks without `document_id` plus 254 chunks belonging to two known `FAILED` documents. The local remediation created a snapshot and removed exactly those 337 derived chunks; a post-cleanup audit reported consistent stores. Current reconciliation repair still intentionally reports these categories rather than repairing them automatically.

## R07 - Controlled drift detection and recovery

**Status:** `passed`
**Evidence type:** Manual local controlled recovery
**Scope:** One derived TXT vector was deliberately removed from the isolated R01 subject. PostgreSQL metadata and the retained source file were not modified.

| Step | Observed result |
| --- | --- |
| Controlled mutation | Deleted 1 Chroma chunk for document `4d4172b8-83e1-4ece-b678-387504916c27` |
| Audit after mutation | 801 Chroma chunks; 1 missing indexed document, matching the intended document |
| Repair dry-run | Planned exactly one `rebuild_document` action for the intended document |
| Repair apply | Exit code 0; rebuilt 1 document and 1 chunk; 0 failed actions |
| Apply duration | 15.826 s |
| Audit after apply | 802 Chroma chunks; 0 missing indexed documents |
| Rebuilt lineage | One chunk restored with `storage_basics.txt`, the R01 subject ID, and lines 1-3 |

### Observed checks

- Detection identified the intended missing derived record before mutation was applied.
- Dry-run separated the recovery plan from the mutation step.
- Apply rebuilt only the planned document from its retained source.
- The controlled document was no longer missing after apply.
- Pre-existing F02 drift remained visible and was not changed by this exercise.

### Limitations

- The full audit exited nonzero at the time because F02 remained unresolved.
- At the time of this case, the rebuilt chunk received a new `chunk_id`, consistent with then-open F01.

## R08 - Stale ingestion recovery

**Status:** `passed`
**Evidence type:** Manual local controlled recovery
**Scope:** A separate isolated subject and one TXT document with a valid retained local source.

| Step | Observed result |
| --- | --- |
| Isolated subject | `2feac95c-4adf-452a-b498-1e7e71e60371` |
| Initial document | `e7d26acb-58f1-457c-9317-ee40abcc1e92` |
| Initial upload | `HTTP 201`; 1 chunk; 4.678 s |
| Controlled stale state | `PROCESSING` at `EMBEDDING` with a heartbeat older than five minutes |
| Recovery dry-run | Exactly 1 candidate, matching the intended document; exit code 0; 0.801 s |
| Recovery apply | Discovered 1, recovered 1, failed 0; exit code 0; 12.357 s |
| Post-recovery lifecycle | `INDEXED`; `current_stage=null`; `processing_attempt_count=2` |
| Post-recovery derived state | 1 Chroma chunk with `storage_distractor.txt`, lines 1-3 |
| Retained-source metadata | Complete |

### Observed checks

- The dry-run identified only the controlled stale document before any recovery mutation.
- Apply reused the retained source and restored the same document identity.
- The recovered document returned to `INDEXED` with valid source lineage and one derived chunk.

### Limitations

- The stale state was created through a controlled database-state mutation; it does not simulate an actual process crash, worker outage, or unavailable source storage.
- This exercise covers one local-storage TXT document only.

## Evidence run conclusion

All R01-R08 cases now have observed results.

| Area | Result |
| --- | --- |
| Evidence collection | Complete |
| Valid ingestion, validation, duplicate protection, retry, lifecycle, controlled repair, and stale recovery | Demonstrated within the stated local scopes |
| Local PostgreSQL-Chroma consistency | Failed during the original evidence run because F02 was open; remediated locally afterward |
| Stable chunk identity | Failed during the original evidence run; remediated with later local runtime evidence |
| Production readiness or private-beta authorization | Not established by this evidence run |

At the end of the original evidence run, the reliability objective was not approved as complete until F01 and F02 were resolved or their contracts were explicitly revised. Both findings were remediated locally afterward; the remaining operational and private-beta boundaries are unchanged.

## Post-evidence F02 remediation

**Status:** `remediated locally`
**Scope:** Exact Chroma cleanup after an inventory-only review. PostgreSQL rows, subjects, and retained sources were not deleted.

| Check | Observed result |
| --- | --- |
| Snapshot target count | 337 derived chunks |
| Snapshot composition | 83 `missing_lineage` chunks and 254 chunks for known non-expected documents |
| Snapshot SHA-256 | `5c5624decb0c9e42a29821d85b25d567a8ae13bedd48a4926014db6bf4bef76a` |
| Cleanup result | 337 of 337 exact snapshot chunk IDs deleted from Chroma |
| Post-cleanup reconciliation | `Expected documents: 10`, `Chroma chunks: 466`, zero missing indexed documents, zero missing-lineage chunks, zero unknown chunks, zero known non-expected documents, and zero subject mismatches |
| Post-cleanup audit | `Stores are consistent.` with exit code 0 in 2.238 s |
| Prevention guard | Pipeline failures now attempt `delete_by_document_id` before recording `FAILED`; focused regression tests and the full backend suite passed |

### Remaining limitation

- This was a local, operator-approved cleanup based on a local snapshot. Future report-only drift must follow the documented snapshot, classification, review, exact-ID manifest, apply, and verification procedure in [`RECONCILIATION_REPORT_ONLY_DRIFT_POLICY.md`](./RECONCILIATION_REPORT_ONLY_DRIFT_POLICY.md). The application still has no generic automatic cleanup for these categories.

## Post-evidence F01 remediation

**Status:** `remediated with local runtime evidence`

**Application commit:** `054f9396a71aa47ff29224cbbbf9e60a679eb19e`

**Scope:** One fresh isolated local subject with self-created TXT, DOCX, and PDF fixtures.

| Check | Observed result |
| --- | --- |
| Evidence subject | `phase25-evidence-20261028-f01` (`3abf0ef4-3568-49bb-8ff8-72c3cc4801a4`) |
| Implementation verification | Full backend suite: `325 passed, 3 skipped, 1 warning` |
| Initial documents | Three `INDEXED` documents; one Chroma chunk per TXT, DOCX, and PDF fixture |
| Baseline identity | Recorded all three `chunk_id` values, their `document_id` values, and format-aware source locations before Trash |
| Trash | `HTTP 200`; subject reached `DELETED`; `processed_documents=3`; `deleted_chunks=3` |
| Restore | `HTTP 200`; subject returned to `ACTIVE`; `processed_documents=3`; `indexed_chunks=3` |
| Post-restore comparison | All three chunk IDs, document IDs, and source locations matched the pre-Trash baseline exactly |
| Post-restore reconciliation | `Expected documents: 13`, `Chroma chunks: 469`, all drift categories zero, `Stores are consistent.`, exit code `0` in `2.426 s` |

### Remaining limitation

- Runtime evidence used one chunk per fixture. Deterministic multi-chunk behavior is covered by automated chunker and pipeline tests, but it has not yet been manually exercised with a large multi-chunk source.
- This local result does not establish production readiness or authorize a private beta.
