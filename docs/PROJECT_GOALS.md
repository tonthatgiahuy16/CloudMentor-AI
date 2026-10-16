# CloudMentor AI — Project Goals and Expected Outcomes

> This document describes **why the project exists** and what the completed platform should achieve. It is a target, not a claim about the current build. Use [Target Architecture](./TARGET_ARCHITECTURE.md) for design decisions and [Project Status](./PROJECT_STATUS.md) for implementation evidence.

## 1. Purpose

CloudMentor AI aims to turn learning documents and learner activity into a connected learning loop: reliable knowledge ingestion, answers with inspectable sources, structured practice, progress analysis, and recommendations for what to study next. The project is intended to demonstrate Data Engineering as the foundation shared by RAG, Quiz, Analytics, and Machine Learning, rather than a collection of disconnected features.

```text
Documents -> Data Platform -> Knowledge -> RAG / Quiz
          -> Learning Records -> Analytics -> ML when justified
          -> Recommended Next Activity
```

## 2. Goals

### Product goal

A learner should be able to organize material by subject, find an answer grounded in the material, practise with a quiz, see where they struggle, and receive a next activity supported by their learning history. The complete product requires two connected data domains:

- **Knowledge data:** subjects, documents, topics or chapters, chunks, embeddings, and source references.
- **Learning data:** users, quizzes, questions, attempts, answers, scores, timestamps, and progress.

### Engineering goal

Build a data platform whose results can be checked and whose failures can be repaired. The intended capabilities are:

- A common document contract for PDF, TXT, DOCX, and any later supported source, with testable Extract, Transform, Chunk, Embed, and Index stages.
- Stable `document_id` and `chunk_id`, plus subject, page, source, and version metadata across write and read paths.
- PostgreSQL as the system of record for relational data and lifecycle; Chroma as a derived retrieval index that can be deleted and rebuilt from retained canonical content.
- Explicit lifecycle, validation, retry and idempotency rules; data quality checks at stage boundaries; logs and metrics sufficient to find affected records and recover.
- Event transport and distributed processing only when a measured workload or product requirement justifies Kafka or Spark.
- Curated, traceable learning datasets before training a personalization model.

### Learning and portfolio goal

The project owner aims to learn and explain the full data lifecycle: the problem, source and output contracts, storage boundaries, failure modes, trade-offs, tests, and measured outcomes. This is a learning objective; a portfolio or CV may claim only the subset supported by current code and evidence in [Project Status](./PROJECT_STATUS.md).

## 3. Expected outcomes when the full roadmap is complete

### Reliable knowledge pipeline

A supported document can be ingested, validated, indexed, queried, deleted from active use, and recovered or rebuilt using stable identity. A failed or repeated operation does not silently create duplicate business effects. The canonical source remains available for recovery, and PostgreSQL and Chroma can be reconciled.

### Traceable RAG

An answer is constrained to retrieved material in the requested scope and carries references sufficient to inspect the source document, page, and chunk. Retrieval relevance, citation correctness, and answer faithfulness are evaluated on a curated set; merely displaying a citation is not proof of correctness.

### Measurable learning

Quiz attempts produce complete records that can be queried by user, subject, chapter or topic, and time. Analytics can identify weak topics, difficult questions, and progress over time. The system measures data completeness and correctness before using those records for decisions.

### Justified personalization

Historical, versioned learning data can support a simple baseline and, if it adds measurable value, a Machine Learning model for weak-topic prediction or next-activity ranking. Recommendations link back to their input data and model or rule version. Improvement in learning outcomes must be measured before claiming that personalization works better.

## 4. Completion evidence

The final outcomes above become implementation claims only after the relevant capability has:

1. A documented input, output, identity, and ownership boundary.
2. Reproducible tests or a recorded manual run covering normal and important failure paths.
3. Data quality and consistency checks for its stored outputs.
4. A recovery path for retries, partial failure, deletion, or rebuild where applicable.
5. Evidence of user or learning value where the claim concerns analytics or recommendations.

Use [Project Status](./PROJECT_STATUS.md) to record the exact commit, test or runtime evidence, remaining limitations, and the difference between implemented, manually verified, and planned work. No fixed throughput, accuracy, scale, or learning-improvement number is asserted here before measurement.

## 5. Scope and sequencing

Deliver a small, trustworthy document-to-answer slice first. Strengthen reproducibility, lifecycle, durable source retention, idempotency, reconciliation, and multi-source ingestion before expanding the learning application. Add Quiz and attempt history before analytics; add Kafka, Spark, and ML when latency, volume, processing complexity, or measured product value creates a concrete need. The phase boundaries and component responsibilities are in [Target Architecture](./TARGET_ARCHITECTURE.md).

The source document *CloudMentor_AI_Project_Goals_and_Final_Outcomes.docx* (19 August 2026) also contains interview examples. Those examples describe an intended full platform and include an old progress snapshot; they are not evidence of current implementation. Current answers for an interview must be rebuilt from [Project Status](./PROJECT_STATUS.md).
