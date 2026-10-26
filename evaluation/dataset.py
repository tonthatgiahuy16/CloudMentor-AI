from pathlib import Path
from pypdf import PdfReader
from app.rag.loader import read_docx_paragraphs

def validate_dataset(dataset: dict, dataset_dir: Path) -> None:
    if dataset.get("schema_version") != "1.0":
        raise ValueError("unsupported schema_version")

    sources_by_id = {}
    location_counts = {}

    for source in dataset["sources"]:
        source_id = source["source_id"]

        if source_id in sources_by_id:
            raise ValueError(f"duplicate source_id: {source_id}")

        source_format = source["format"]

        if source_format not in {"txt", "docx", "pdf"}:
            raise ValueError(f"unsupported format: {source_format}")

        source_path = Path(dataset_dir) / source["path"]

        if source_path.suffix.lower() != f".{source_format}":
            raise ValueError(f"invalid source path: {source_path}")

        if not source_path.is_file():
            raise ValueError(f"missing fixture: {source_path}")

        sources_by_id[source_id] = source

        if source_format == "txt":
            location_counts[source_id] = len(
                source_path.read_text(
                    encoding="utf-8-sig"
                ).splitlines()
            )
        elif source_format == "docx":
            location_counts[source_id] = len(
                read_docx_paragraphs(source_path)
            )
        else:
            location_counts[source_id] = len(
                PdfReader(source_path).pages
            )

    case_ids = set()
    known_subjects = {
        source["subject_key"]
        for source in sources_by_id.values()
    }

    for case in dataset["cases"]:
        case_id = case["case_id"]

        if case_id in case_ids:
            raise ValueError(f"duplicate case_id: {case_id}")

        case_ids.add(case_id)

        if case["subject_key"] not in known_subjects:
            raise ValueError(f"unknown subject_key: {case_id}")

        answerable = case["answerable"]
        evidence = case["expected_evidence"]
        facts = case["expected_facts"]

        if not isinstance(answerable, bool):
            raise ValueError(f"answerable must be a boolean: {case_id}")

        if answerable and (not evidence or not facts):
            raise ValueError(f"missing expected data: {case_id}")

        if not answerable and (evidence or facts):
            raise ValueError(f"unexpected expected data: {case_id}")

        for item in evidence:
            source_id = item["source_id"]

            if source_id not in sources_by_id:
                raise ValueError(f"unknown source_id: {source_id}")

            source = sources_by_id[source_id]

            if source["subject_key"] != case["subject_key"]:
                raise ValueError(f"subject mismatch: {case_id}")

            if source["format"] == "pdf":
                if set(item) != {"source_id", "page"}:
                    raise ValueError(f"invalid evidence location: {case_id}")

                page = item["page"]

                if type(page) is not int or not 1 <= page <= location_counts[source_id]:
                    raise ValueError(f"page out of bounds: {case_id}")

                continue

            location_key = (
                "line_range"
                if source["format"] == "txt"
                else "paragraph_range"
            )

            if set(item) != {"source_id", location_key}:
                raise ValueError(f"invalid evidence location: {case_id}")

            location_range = item[location_key]

            if (
                not isinstance(location_range, list)
                or len(location_range) != 2
                or any(type(value) is not int for value in location_range)
            ):
                raise ValueError(f"invalid {location_key}: {case_id}")

            start, end = location_range

            if not 1 <= start <= end <= location_counts[source_id]:
                raise ValueError(f"{location_key} out of bounds: {case_id}")
