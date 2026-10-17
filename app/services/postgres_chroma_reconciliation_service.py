from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectMismatch:
    chunk_id: str
    document_id: str
    expected_subject_id: str
    actual_subject_id: str | None


@dataclass(frozen=True)
class KnownNonExpectedDocument:
    document_id: str
    subject_id: str
    document_status: str
    subject_status: str
    chunk_count: int


@dataclass(frozen=True)
class ReconciliationReport:
    known_nonexpected_documents: tuple[
        KnownNonExpectedDocument,
        ...,
    ]
    expected_document_count: int
    actual_chunk_count: int
    missing_document_ids: tuple[str, ...]
    missing_lineage_chunk_ids: tuple[str, ...]
    orphan_chunk_ids: tuple[str, ...]
    subject_mismatches: tuple[
        SubjectMismatch,
        ...,
    ]

    @property
    def is_consistent(self) -> bool:
        return not (
            self.missing_document_ids
            or self.missing_lineage_chunk_ids
            or self.orphan_chunk_ids
            or self.subject_mismatches
            or self.known_nonexpected_documents
        )


class PostgresChromaReconciliationService:
    def __init__(
        self,
        *,
        document_repo,
        vector_store,
    ):
        self.document_repo = document_repo
        self.vector_store = vector_store

    def audit(self) -> ReconciliationReport:
        nonexpected_records: list[dict] = []

        documents = (
            self.document_repo
            .list_indexed_for_active_subjects()
        )
        records = (
            self.vector_store
            .list_all_records()
        )

        expected_subjects = {
            document.document_id: document.subject_id
            for document in documents
        }

        document_ids_with_chunks: set[str] = set()
        missing_lineage_chunk_ids: list[str] = []
        orphan_chunk_ids: list[str] = []
        subject_mismatches: list[
            SubjectMismatch
        ] = []

        for record in records:
            chunk_id = record["chunk_id"]
            document_id = record.get("document_id")
            actual_subject_id = record.get(
                "subject_id"
            )

            if not document_id:
                missing_lineage_chunk_ids.append(
                    chunk_id
                )
                continue

            if document_id not in expected_subjects:
                nonexpected_records.append(record)
                continue

            document_ids_with_chunks.add(
                document_id
            )

            expected_subject_id = (
                expected_subjects[document_id]
            )

            if (
                actual_subject_id
                != expected_subject_id
            ):
                subject_mismatches.append(
                    SubjectMismatch(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        expected_subject_id=(
                            expected_subject_id
                        ),
                        actual_subject_id=(
                            actual_subject_id
                        ),
                    )
                )

        known_documents_by_id = {}
        known_nonexpected_counts: dict[
            str,
            int,
        ] = {}

        if nonexpected_records:
            reconciliation_records = (
                self.document_repo
                .list_reconciliation_records()
            )

            known_documents_by_id = {
                record.document_id: record
                for record
                in reconciliation_records
            }

            for record in nonexpected_records:
                chunk_id = record["chunk_id"]
                document_id = record[
                    "document_id"
                ]

                if (
                    document_id
                    not in known_documents_by_id
                ):
                    orphan_chunk_ids.append(
                        chunk_id
                    )
                    continue

                known_nonexpected_counts[
                    document_id
                ] = (
                    known_nonexpected_counts.get(
                        document_id,
                        0,
                    )
                    + 1
                )

        missing_document_ids = tuple(
            sorted(
                set(expected_subjects)
                - document_ids_with_chunks
            )
        )

        known_nonexpected_documents = tuple(
            KnownNonExpectedDocument(
                document_id=document_id,
                subject_id=(
                    known_documents_by_id[
                        document_id
                    ].subject_id
                ),
                document_status=(
                    known_documents_by_id[
                        document_id
                    ].document_status
                ),
                subject_status=(
                    known_documents_by_id[
                        document_id
                    ].subject_status
                ),
                chunk_count=chunk_count,
            )
            for document_id, chunk_count
            in sorted(
                known_nonexpected_counts.items()
            )
        )

        return ReconciliationReport(
            expected_document_count=len(
                expected_subjects
            ),
            actual_chunk_count=len(records),
            missing_document_ids=(
                missing_document_ids
            ),
            missing_lineage_chunk_ids=tuple(
                sorted(
                    missing_lineage_chunk_ids
                )
            ),
            orphan_chunk_ids=tuple(
                sorted(orphan_chunk_ids)
            ),
            known_nonexpected_documents=(
                known_nonexpected_documents
            ),
            subject_mismatches=tuple(
                sorted(
                    subject_mismatches,
                    key=lambda mismatch: (
                        mismatch.chunk_id
                    ),
                )
            ),
        )
