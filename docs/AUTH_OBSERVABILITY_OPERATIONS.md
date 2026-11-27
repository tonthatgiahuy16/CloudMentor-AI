# Authentication, observability, and retrieval operations

This note records the access policy and operator workflows added in the
current working tree. It is not a production security review.

## Identities and roles

Users live in the `users` table:

- `employee_id` is unique and is the login name.
- `password_hash` uses Argon2id through `argon2-cffi`.
- `role` is `admin` or `employee`.
- Deactivating a user invalidates new requests even if an old token has
  not expired yet.

Create or update a user without putting the password in shell history:

```powershell
python -m scripts.create_user --employee-id admin --role admin
python -m scripts.create_user --employee-id alice --role employee
```

`POST /auth/token` accepts an OAuth2 password form (`username` is the
employee id) and returns a short-lived HS256 bearer token. Set
`JWT_SECRET` to a long random value; without it, development falls back
to a process-local secret that changes on restart.

## Route policy

Public routes: `/`, `/healthz`, `/readyz`, `/auth/token`,
`/internal/demo-seed`.

Authenticated routes: subject listing, chat, quiz listing/detail,
starting an attempt, and reading or submitting the caller's own attempt.

Admin routes: document and upload mutations, subject trash, quiz
authoring and publication, quiz overview and attempt listing, and
pipeline metrics.

Attempt access rules:

- An employee may read and submit only their own attempt.
- An administrator may read any attempt for training analytics, but may
  not submit on behalf of an employee.
- A missing attempt and a foreign attempt both return `404`, so attempt
  IDs cannot be enumerated.
- The attempt owner comes from the token, not the request body.

Answer-key policy:

- `correct_option_id` is never included in `QuizPublic` before an attempt
  is submitted.
- It is revealed only in the owner's or an administrator's result after
  submission, which supports reviewing the completed quiz.
- Retakes remain allowed because these are training quizzes; this policy
  should be revisited if a quiz becomes a one-time certification.

## Observability

`RequestContextMiddleware` accepts or generates `X-Request-ID`, returns
it in the response, and attaches it to JSON logs. The logger redacts
sensitive keys and common credential patterns; it must still not be used
to log document content, prompts, or questions.

Each pipeline stage (`EXTRACT`, `TRANSFORM`, `CHUNK`, `EMBEDDING`,
`INDEX`) writes a row to `document_processing_events` with `status`,
`duration_ms`, optional `error_code`, and the request id. Metrics are
aggregated from PostgreSQL, not scraped from log files:

```text
GET /metrics/pipeline?window_days=7
```

The response includes per-stage run/failure counts, average and p50/p95
durations, document status counts, and recent failures. Percentiles are
computed in Python over a bounded event window (50,000 rows).

## Retrieval threshold and vector space

Chroma collections are created with `hnsw:space = cosine`. `VectorStore.__init__` fails fast with a `RuntimeError` if an existing collection uses a different distance space (such as legacy `l2`), requiring an explicit rebuild before the API can serve or index into it. The retriever compares cosine distance with `1 - MIN_COSINE_SIMILARITY`, so a value of `0.50` means "keep chunks at cosine similarity 0.50 or higher".

Calibrate the threshold from observed distances instead of guessing:

```powershell
python -m evaluation.run_threshold_calibration `
  --dataset evaluation/cases.json `
  --subjects evaluation/subjects.json `
  --output evaluation/threshold_calibration.json
```

The report sweeps minimum similarity, shows answerable hit rate and false
answers on unanswerable cases, and recommends a cutoff while keeping the
answerable hit rate at or above `--min-hit-rate` (default `0.9`).

Changing the collection from L2 to cosine cannot be done in place. Stop
the API, run the dry run first, then apply the rebuild from PostgreSQL
and retained sources:

```powershell
python -m scripts.rebuild_vector_collection
python -m scripts.rebuild_vector_collection --apply
```

The rebuild deletes and recreates the derived collection, so retrieval is
empty until it finishes. PostgreSQL remains the system of record.
