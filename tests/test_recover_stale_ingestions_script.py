from types import SimpleNamespace
from unittest.mock import Mock

import scripts.recover_stale_ingestions as recovery_script


def test_apply_injects_source_storage_into_pdf_service(
    monkeypatch,
):
    db = Mock()
    document_repo = Mock()
    document_repo.list_stale_ingestions.return_value = []

    source_storage = Mock()
    pdf_service = Mock()
    recovery_service = Mock()
    recovery_service.recover.return_value = {
        "discovered": 0,
        "recovered": 0,
        "failed": 0,
        "failures": [],
    }

    get_source_storage = Mock(
        return_value=source_storage
    )
    pdf_service_class = Mock(
        return_value=pdf_service
    )
    recovery_service_class = Mock(
        return_value=recovery_service
    )

    monkeypatch.setattr(
        recovery_script,
        "parse_args",
        Mock(
            return_value=SimpleNamespace(
                stale_after_minutes=60,
                apply=True,
            )
        ),
    )
    monkeypatch.setattr(
        recovery_script,
        "SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        recovery_script,
        "DocumentRepository",
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        recovery_script,
        "PDFService",
        pdf_service_class,
    )
    monkeypatch.setattr(
        recovery_script,
        "IngestionRecoveryService",
        recovery_service_class,
    )
    monkeypatch.setattr(
        recovery_script,
        "get_source_storage",
        get_source_storage,
        raising=False,
    )

    result = recovery_script.main()

    assert result == 0
    get_source_storage.assert_called_once_with()
    pdf_service_class.assert_called_once_with(
        document_repo,
        source_storage=source_storage,
    )
    recovery_service_class.assert_called_once_with(
        document_repo=document_repo,
        pdf_service=pdf_service,
    )
    db.close.assert_called_once_with()
