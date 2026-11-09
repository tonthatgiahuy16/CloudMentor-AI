# CloudMentor AI — Project Goals and Expected Outcomes

> This document describes the product direction and expected outcomes. It is a target, not a claim that every capability is implemented. See [Target Architecture](./TARGET_ARCHITECTURE.md) for design and [Project Status](./PROJECT_STATUS.md) for evidence from the current build.

## 1. Purpose

CloudMentor AI is an **Enterprise Policy and Onboarding Platform**. It helps employees find answers grounded in company policies and helps training owners prepare reviewed onboarding assessments and inspect completion results. Data Engineering is the backbone: reliable ingestion, lifecycle management, traceability, and recovery support the search, quiz, and reporting experiences.

```text
Company policy documents -> validated data pipeline -> versioned knowledge
                                                   -> grounded policy answers
                                                   -> reviewed onboarding quizzes
Employee quiz attempts -> reliable records -> training overview and follow-up
```

The current MVP is intentionally a single-company demo using sample identities and sample policy content. It is not a legal decision system or a production HR compliance system.

## 2. Primary actors

- **Training Admin:** manages policy documents and their effective dates, creates or reviews onboarding quizzes, publishes approved quizzes, and views training completion summaries.
- **Employee:** looks up current policy information, completes assigned or available onboarding quizzes, and reviews personal results and referenced policy material.

These are product roles. The current demo's separate workspaces do not provide authenticated identity or backend-enforced authorization; access control is a future requirement before real employee or multi-company use.

## 3. Goals

### Product goals

- Give employees answers based on policies applicable on the requested business date, with visible document and location references.
- Keep policy versions traceable, including effective windows and the source version used by a quiz question.
- Let training owners create and review question sets before publication; grading must use the approved answer key stored by the application.
- Record quiz attempts and answers so employees can review their work and training owners can see completion and aggregate outcomes.
- Make the current policy state, unavailable data, and source provenance clear instead of presenting unsupported answers as authoritative.

### Data Engineering goals

- Treat PostgreSQL as the system of record for document identity, policy applicability, quiz definitions, answer keys, and attempts.
- Treat Chroma as a derived retrieval index that can be reconciled and rebuilt from retained source material and PostgreSQL state.
- Preserve stable identities and lineage from source document/version through extracted content, chunks, retrieval citations, quiz questions, and quiz results where applicable.
- Define validation, lifecycle, retry, idempotency, consistency, and recovery behavior at data boundaries.
- Add observability and measured data-quality checks before increasing operational complexity.
- Introduce Kafka, Spark, or Machine Learning only when workload evidence or a measured product need justifies them.

### Learning and portfolio goal

The project owner aims to learn and explain the complete data lifecycle: source contracts, pipeline stages, storage boundaries, failure modes, trade-offs, tests, and measured outcomes. Portfolio claims must describe the implemented and evidenced subset in [Project Status](./PROJECT_STATUS.md), distinguishing local verification, user-reported end-to-end checks, and planned work.

## 4. Expected outcomes as the platform matures

### Governed policy knowledge

A policy can be ingested, validated, versioned, assigned an effective window, retrieved only while applicable, and cited back to its source. PostgreSQL determines applicability; stale or inconsistent derived vectors must not make an obsolete version eligible. Operators have a documented way to detect and repair index drift.

### Reviewed onboarding assessments

Training owners can prepare and review quizzes tied to policy source versions. Published questions have stable answer keys; the server grades submissions and stores attempts. Draft generation, if introduced, is assistance only and does not establish a correct answer without review.

### Useful training records

Employees can inspect their quiz results and cited material. Training owners can inspect completion and aggregate outcomes. Any analytics must have clear definitions, appropriate data access, and retention rules; scores are not employment or legal-compliance determinations.

### Safe organizational growth

Before supporting real companies or employee identities, the platform must add authentication, backend authorization, tenant isolation, data minimization, and retention/deletion rules, then verify those boundaries with tests. Production operations also require independent backups, restore exercises, monitoring, and shared rate limiting.

## 5. Completion evidence

Treat a capability as implemented only when its documented input/output and ownership boundaries are backed by code, relevant automated or reproducible manual checks, data-quality and consistency checks, and a recovery path where needed. Product-value claims require user evidence; accuracy, throughput, scale, and learning-improvement claims require measurement. See [Project Status](./PROJECT_STATUS.md) for the current snapshot and limitations.

## 6. Scope and sequencing

The current demo establishes three slices: policy versioning and date-aware retrieval; persisted onboarding quizzes with server-side grading and provenance; and employee/training-admin demo workspaces. Next, strengthen security, operational recovery, and observability before using real employee records or presenting the system as production-ready. Advanced analytics, event streaming, distributed processing, and ML remain future options driven by evidence rather than MVP requirements.

The source document *CloudMentor_AI_Project_Goals_and_Final_Outcomes.docx* (19 August 2026) describes an earlier individual learning-product direction and contains an old progress snapshot. It is historical context, not the current product goal or implementation evidence.
