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


@dataclass(frozen=True)
class ReconciliationRepairPlan:
    delete_orphan_chunk_ids: tuple[str, ...]
    rebuild_document_ids: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (
            self.delete_orphan_chunk_ids
            or self.rebuild_document_ids
        )


@dataclass(frozen=True)
class ReconciliationRepairFailure:
    action: str
    target_id: str
    error_message: str


@dataclass(frozen=True)
class ReconciliationRepairResult:
    deleted_orphan_chunk_ids: tuple[str, ...]
    rebuilt_document_ids: tuple[str, ...]
    rebuilt_chunk_count: int
    failed_actions: tuple[
        ReconciliationRepairFailure,
        ...,
    ] = ()

    @property
    def is_successful(self) -> bool:
        return not self.failed_actions


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

    def plan_repair(self) -> ReconciliationRepairPlan:
        report = self.audit()

        return ReconciliationRepairPlan(
            delete_orphan_chunk_ids=report.orphan_chunk_ids,
            rebuild_document_ids=report.missing_document_ids,
        )

    def apply_repair(
        self,
        *,
        document_rebuilder,
    ) -> ReconciliationRepairResult:
        plan = self.plan_repair()

        deleted_orphan_chunk_ids = []
        failed_actions = []

        for chunk_id in plan.delete_orphan_chunk_ids:
            try:
                self.vector_store.delete_by_chunk_ids(
                    [chunk_id]
                )
                deleted_orphan_chunk_ids.append(chunk_id)
            except Exception as exc:
                failed_actions.append(
                    ReconciliationRepairFailure(
                        action="delete_orphan_chunk",
                        target_id=chunk_id,
                        error_message=str(exc),
                    )
                )

        current_documents = {
            document.document_id: document
            for document in (
                self.document_repo
                .list_indexed_for_active_subjects()
            )
        }

        rebuilt_document_ids = []
        rebuilt_chunk_count = 0

        for document_id in plan.rebuild_document_ids:
            document = current_documents.get(document_id)

            if document is None:
                continue

            try:
                rebuilt_chunk_count += document_rebuilder(
                    document
                )
                rebuilt_document_ids.append(document_id)
            except Exception as exc:
                failed_actions.append(
                    ReconciliationRepairFailure(
                        action="rebuild_document",
                        target_id=document_id,
                        error_message=str(exc),
                    )
                )

        return ReconciliationRepairResult(
            deleted_orphan_chunk_ids=(
                tuple(deleted_orphan_chunk_ids)
            ),
            rebuilt_document_ids=tuple(
                rebuilt_document_ids
            ),
            rebuilt_chunk_count=rebuilt_chunk_count,
            failed_actions=tuple(failed_actions),
        )
