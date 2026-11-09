class PolicyVersionService:
    """Activate indexed policy versions after verifying Chroma lineage."""

    def __init__(self, document_repo, vector_store):
        self.document_repo = document_repo
        self.vector_store = vector_store

    def activate(
        self,
        *,
        document_id: str,
        effective_from,
        supersedes_document_id: str | None = None,
    ):
        document = self.document_repo.get_by_id(document_id)
        if document is None:
            raise RuntimeError("Document not found")
        if document.status != "INDEXED":
            raise RuntimeError(
                "Only indexed documents can be activated"
            )
        if document.indexed_chunk_count is None:
            raise RuntimeError(
                "Document index has not been verified"
            )

        actual_chunk_count = self.vector_store.count_by_document_id(
            document_id
        )
        if actual_chunk_count != document.indexed_chunk_count:
            raise RuntimeError(
                "Indexed chunk count does not match PostgreSQL"
            )

        return self.document_repo.activate_policy_version(
            document_id=document_id,
            effective_from=effective_from,
            supersedes_document_id=supersedes_document_id,
        )
