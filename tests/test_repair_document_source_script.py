from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from scripts.repair_document_source import main


def test_main_defaults_to_dry_run(
    tmp_path,
    monkeypatch,
    capsys,
):
    source_path = tmp_path / "lesson.pdf"
    upload_dir = tmp_path / "uploads"

    plan = SimpleNamespace(
        document_id="legacy-document-id",
        source_path=source_path,
        target_path=(
            upload_dir
            / "legacy-document-id_lesson.pdf"
        ),
        source_uri=(
            upload_dir
            / "legacy-document-id_lesson.pdf"
        ).as_posix(),
        content_sha256="a" * 64,
        file_size_bytes=100,
    )

    db = Mock()
    document_repo = Mock()
    repair_service = Mock()
    repair_service.plan.return_value = plan

    monkeypatch.setattr(
        "scripts.repair_document_source.SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        "scripts.repair_document_source.DocumentRepository",
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        (
            "scripts.repair_document_source."
            "DocumentSourceRepairService"
        ),
        Mock(return_value=repair_service),
    )

    exit_code = main(
        [
            "--document-id",
            "legacy-document-id",
            "--source-path",
            str(source_path),
            "--upload-dir",
            str(upload_dir),
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Dry run only" in output

    repair_service.plan.assert_called_once_with(
        document_id="legacy-document-id",
        source_path=Path(source_path),
    )
    repair_service.apply.assert_not_called()
    db.close.assert_called_once_with()


def test_main_applies_repair_when_requested(
    tmp_path,
    monkeypatch,
    capsys,
):
    source_path = tmp_path / "lesson.pdf"
    upload_dir = tmp_path / "uploads"

    plan = SimpleNamespace(
        document_id="legacy-document-id",
        source_path=source_path,
        target_path=(
            upload_dir
            / "legacy-document-id_lesson.pdf"
        ),
        source_uri=(
            upload_dir
            / "legacy-document-id_lesson.pdf"
        ).as_posix(),
        content_sha256="a" * 64,
        file_size_bytes=100,
    )

    db = Mock()
    document_repo = Mock()
    repair_service = Mock()
    repair_service.plan.return_value = plan

    monkeypatch.setattr(
        "scripts.repair_document_source.SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        "scripts.repair_document_source.DocumentRepository",
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        (
            "scripts.repair_document_source."
            "DocumentSourceRepairService"
        ),
        Mock(return_value=repair_service),
    )

    exit_code = main(
        [
            "--document-id",
            "legacy-document-id",
            "--source-path",
            str(source_path),
            "--upload-dir",
            str(upload_dir),
            "--apply",
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert (
        "Document source repair completed."
        in output
    )
    repair_service.apply.assert_called_once_with(
        plan
    )
    db.close.assert_called_once_with()
