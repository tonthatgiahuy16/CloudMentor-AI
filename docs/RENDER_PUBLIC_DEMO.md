# Render public demo runbook

This runbook deploys a deliberately constrained public demo. It is not a
production-readiness claim: it has no authentication, backup automation,
multi-instance rate-limit store, or monitoring/alerting.

## Provisioning

1. Push the reviewed files to the Git repository, then create a Render
   Blueprint from `render.yaml`.
2. During Blueprint creation, set `GEMINI_API_KEY` only in Render's secret
   field. Do not put it in Git, the frontend, or a browser environment
   variable.
3. After Render assigns URLs, configure both values and redeploy in this
   order:

   - API `CORS_ALLOWED_ORIGINS`: the exact static-site origin, for example
     `https://cloudmentor-demo-web.onrender.com`.
   - Static site `VITE_API_URL`: the complete API origin, for example
     `https://cloudmentor-demo-api.onrender.com`.

   `VITE_*` values are compiled into the static bundle, so changing the API
   URL requires a frontend rebuild. Do not use a Render private-network host
   for this value because browsers cannot reach it.
4. Confirm the web service has one instance, one disk mounted at `/data`, and
   `DEMO_MODE=true`. The blueprint sets `/data/sources` as canonical local
   source storage and `/data/chroma` as the derived index.

## Seed before sharing

Only upload three or four documents whose public-demo redistribution rights
are known. Use one narrowly scoped subject, verify each document reaches
`INDEXED`, then ask representative questions and check the returned citations.
After seeding, keep `DEMO_MODE=true`; the API rejects subject creation, upload,
document deletion, subject deletion, and subject restore even if a caller
bypasses the frontend.

## Release checks

1. Confirm `GET /healthz` returns `200` and `GET /readyz` returns `200`.
2. Confirm the frontend lists the seeded sources and answers a subject-scoped
   question with sources.
3. Confirm a direct `POST /subjects/` and `POST /upload/` return `403`.
4. Send more than `CHAT_RATE_LIMIT_PER_MINUTE` chat requests from one IP and
   confirm the next response is `429`.
5. Verify browser CORS permits only the configured static-site origin.

## Operating boundaries

- PostgreSQL is the system of record. Chroma under `/data/chroma` is derived
  and can be rebuilt from retained source files and PostgreSQL metadata.
- Render's persistent disk survives restarts and redeploys only under `/data`.
  It is attached to one runtime instance, is unavailable to pre-deploy
  commands, and does not replace an independent backup.
- The in-memory rate limiter is per API instance. The blueprint intentionally
  pins the service at one instance because the persistent disk also requires a
  single attached instance.
- Test restore/rebuild and an independent PostgreSQL plus `/data` backup
  procedure before describing this deployment as anything beyond a demo.
