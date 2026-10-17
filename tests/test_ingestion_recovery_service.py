from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, call

from app.services.ingestion_recovery_service import (
    IngestionRecoveryService,
)


def test_recover_processes_every_stale_document():
    stale_before = datetime(
        2026,
        10,
        17,
        8,
        0,
        tzinfo=timezone.utc,
    )

    documents = [
        SimpleNamespace(
            document_id="document-1",
        ),
        SimpleNamespace(
            document_id="document-2",
        ),
    ]

    document_repo = Mock()
    document_repo.list_stale_ingestions.return_value = (
        documents
    )

    pdf_service = Mock()
    pdf_service.recover_stale_document.side_effect = [
        3,
        5,
    ]

    service = IngestionRecoveryService(
        document_repo=document_repo,
        pdf_service=pdf_service,
    )

    result = service.recover(
        stale_before=stale_before,
    )

    assert result == {
        "discovered": 2,
        "recovered": 2,
        "failed": 0,
        "failures": [],
    }
    document_repo.list_stale_ingestions.assert_called_once_with(
        stale_before=stale_before,
    )
    assert (
        pdf_service
        .recover_stale_document
        .call_args_list
    ) == [
        call(documents[0]),
        call(documents[1]),
    ]


def test_recover_continues_after_document_failure():
    stale_before = datetime(
        2026,
        10,
        17,
        8,
        0,
        tzinfo=timezone.utc,
    )

    documents = [
        SimpleNamespace(
            document_id="broken-document",
        ),
        SimpleNamespace(
            document_id="recoverable-document",
        ),
    ]

    document_repo = Mock()
    document_repo.list_stale_ingestions.return_value = (
        documents
    )

    pdf_service = Mock()
    pdf_service.recover_stale_document.side_effect = [
        RuntimeError("Retained source file is missing"),
        4,
    ]

    service = IngestionRecoveryService(
        document_repo=document_repo,
        pdf_service=pdf_service,
    )

    result = service.recover(
        stale_before=stale_before,
    )

    assert result == {
        "discovered": 2,
        "recovered": 1,
        "failed": 1,
        "failures": [
            {
                "document_id": "broken-document",
                "error_message": (
                    "Retained source file is missing"
                ),
            }
        ],
    }
    assert (
        pdf_service
        .recover_stale_document
        .call_args_list
    ) == [
        call(documents[0]),
        call(documents[1]),
    ]
