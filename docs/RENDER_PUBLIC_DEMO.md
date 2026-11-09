# Render Public Demo Runbook

This runbook describes the constrained single-company demo configuration in `render.yaml`. It is not a production-readiness claim: the application has no authentication or backend role authorization, automated independent backups, multi-instance rate-limit store, or monitoring and alerting.

## Current demo content boundary

The seed service loads only filenames listed in `demo-sources/manifest.json`. The current manifest lists four Data Engineering documents. `demo-sources/sample_onboarding_policy_2026.txt` is present in the repository but is **not currently listed in that manifest**, so the existing Render seed operation will not load it. To publish an onboarding demo, first update and review the seed manifest and verify the policy's effective date/version activation workflow; then redeploy and seed. Do not describe the onboarding policy as available in a deployed demo until that run is verified.

The onboarding API is under `/quizzes/`: training owners create and publish reviewed quizzes; employees list published quizzes, start attempts, submit answers, and review results. Relevant routes include `POST /quizzes/`, `POST /quizzes/{quiz_id}/questions`, `POST /quizzes/{quiz_id}/publish`, `GET /quizzes/?subject_id=...`, `POST /quizzes/{quiz_id}/attempts`, and `POST /quizzes/attempts/{attempt_id}/submit`. **These quiz mutation routes are also blocked while `DEMO_MODE=true`**, and the seed service currently seeds documents only, not quiz definitions. Therefore the current Render blueprint cannot demonstrate interactive quiz authoring or attempts. That requires a reviewed pre-seeded quiz/read-only attempt design or a deliberately scoped demo-mode change before deployment. The current demo workspaces are frontend navigation states, not identity-backed authorization. Avoid real employee identities or confidential company policies.

## Provisioning

1. Push the reviewed files to the Git repository, then create a Render Blueprint from `render.yaml`.
2. During Blueprint creation, set `GEMINI_API_KEY` only in Render's secret field. Do not put it in Git, the frontend, or a browser environment variable.
3. After Render assigns URLs, configure both values and redeploy in this order:
   - API `CORS_ALLOWED_ORIGINS`: the exact static-site origin, for example `https://cloudmentor-demo-web.onrender.com`.
   - Static site `VITE_API_URL`: the complete API origin, for example `https://cloudmentor-demo-api.onrender.com`.

   `VITE_*` values are compiled into the static bundle, so changing the API URL requires a frontend rebuild. Do not use a Render private-network host for this value because browsers cannot reach it.
4. Confirm the web service has one instance, one disk mounted at `/data`, and `DEMO_MODE=true`. The blueprint sets `/data/sources` as canonical local source storage and `/data/chroma` as the derived index.

## Seed before sharing

The bundled `demo-sources/` files listed in `demo-sources/manifest.json` are the only files accepted by the internal seed route. Set `DEMO_SEED_TOKEN` as a Render secret, call `POST /internal/demo-seed` with that value in `X-Demo-Seed-Token`, then remove the secret and redeploy after a successful seed. The route accepts no upload or source path from a caller. Keep `DEMO_MODE=true`; public mutation routes remain blocked even if a caller bypasses the frontend. Seeding does not create a quiz. Quiz authoring and attempt submission are consequently unavailable in this Render configuration until the demo design is extended as described above.

## Release checks

1. Confirm `GET /healthz` returns `200` and `GET /readyz` returns `200`.
2. Confirm the frontend lists the seeded sources and answers a subject-scoped policy question with citations. For an onboarding demo, verify the onboarding sample is in the seed manifest and is active for the tested business date.
3. Confirm direct `POST /subjects/`, `POST /upload/`, and quiz mutation routes return `403` in demo mode. Quiz creation, attempts, and results must be verified locally until a safe public-demo quiz flow is implemented.
4. Send more than `CHAT_RATE_LIMIT_PER_MINUTE` chat requests from one IP and confirm the next response is `429`.
5. Verify browser CORS permits only the configured static-site origin.

## Operating boundaries

- PostgreSQL is the system of record. Chroma under `/data/chroma` is derived and can be rebuilt from retained source files and PostgreSQL metadata.
- Render's persistent disk survives restarts and redeploys only under `/data`. It is attached to one runtime instance, is unavailable to pre-deploy commands, and does not replace an independent backup.
- The in-memory rate limiter is per API instance. The blueprint intentionally pins the service at one instance because the persistent disk also requires a single attached instance.
- Separate admin and employee screens do not protect data. Add authentication, backend authorization, tenant isolation, and employee-data retention rules before real organizational use.
- Test restore/rebuild and an independent PostgreSQL plus `/data` backup procedure before describing this deployment as anything beyond a demo.
