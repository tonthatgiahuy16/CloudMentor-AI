from evaluation.answer_scoring import score_answer_observation


def test_scores_answerable_response_with_expected_evidence():
    case = {
        "case_id": "storage-001",
        "answerable": True,
        "expected_facts": [
            "The original source file is retained in configured source storage."
        ],
        "expected_evidence": [
            {
                "source_id": "storage-basics-txt",
                "line_range": [2, 2],
            }
        ],
    }
    source_index = {
        "storage-basics-txt": {
            "path": "fixtures/storage_basics.txt",
        }
    }
    observation = {
        "case_id": "storage-001",
        "answer": (
            "Tệp nguồn gốc được giữ trong kho lưu trữ nguồn đã cấu hình."
        ),
        "answer_correct": True,
        "sources": [
            {
                "source": "storage_basics.txt",
                "line_range": [1, 3],
            }
        ],
        "faithful": True,
    }

    assert score_answer_observation(
        case,
        observation,
        source_index,
    ) == {
        "answer_correct": True,
        "citation_hit": True,
        "faithful": True,
        "refusal_correct": None,
    }


def test_scores_unanswerable_response_that_refuses():
    case = {
        "case_id": "backup-002",
        "answerable": False,
        "expected_facts": [],
        "expected_evidence": [],
    }
    observation = {
        "case_id": "backup-002",
        "answer": "Tài liệu cung cấp không nêu lịch sao lưu.",
        "refusal_correct": True,
        "sources": [],
        "faithful": True,
    }

    assert score_answer_observation(
        case,
        observation,
        source_index={},
    ) == {
        "answer_correct": None,
        "citation_hit": None,
        "faithful": True,
        "refusal_correct": True,
    }


def test_rejects_response_with_wrong_citation():
    case = {
        "case_id": "storage-001",
        "answerable": True,
        "expected_facts": [
            "The original source file is retained in configured source storage."
        ],
        "expected_evidence": [
            {
                "source_id": "storage-basics-txt",
                "line_range": [2, 2],
            }
        ],
    }
    source_index = {
        "storage-basics-txt": {
            "path": "fixtures/storage_basics.txt",
        },
        "storage-distractor-txt": {
            "path": "fixtures/storage_distractor.txt",
        },
    }
    observation = {
        "case_id": "storage-001",
        "answer": (
            "The original source file is retained in configured source storage."
        ),
        "answer_correct": True,
        "sources": [
            {
                "source": "storage_distractor.txt",
                "line_range": [1, 3],
            }
        ],
        "faithful": False,
    }

    assert score_answer_observation(
        case,
        observation,
        source_index,
    ) == {
        "answer_correct": True,
        "citation_hit": False,
        "faithful": False,
        "refusal_correct": None,
    }


def test_rejects_unanswerable_response_that_invents_an_answer():
    case = {
        "case_id": "backup-002",
        "answerable": False,
        "expected_facts": [],
        "expected_evidence": [],
    }
    observation = {
        "case_id": "backup-002",
        "answer": "Source files are backed up every day.",
        "refusal_correct": False,
        "sources": [],
        "faithful": False,
    }

    assert score_answer_observation(
        case,
        observation,
        source_index={},
    ) == {
        "answer_correct": None,
        "citation_hit": None,
        "faithful": False,
        "refusal_correct": False,
    }


def test_scores_docx_response_with_paragraph_citation():
    case = {
        "case_id": "ingestion-001",
        "answerable": True,
        "expected_facts": [
            "The transform stage cleans extracted text before chunking."
        ],
        "expected_evidence": [
            {
                "source_id": "ingestion-basics-docx",
                "paragraph_range": [2, 2],
            }
        ],
    }
    source_index = {
        "ingestion-basics-docx": {
            "path": "fixtures/ingestion_basics.docx",
        }
    }
    observation = {
        "case_id": "ingestion-001",
        "answer": "Transform làm sạch văn bản trước khi chunking.",
        "answer_correct": True,
        "sources": [
            {
                "source": "ingestion_basics.docx",
                "paragraph_range": [1, 3],
            }
        ],
        "faithful": True,
    }

    assert score_answer_observation(
        case,
        observation,
        source_index,
    ) == {
        "answer_correct": True,
        "citation_hit": True,
        "faithful": True,
        "refusal_correct": None,
    }


def test_scores_pdf_response_with_page_citation():
    case = {
        "case_id": "validation-001",
        "answerable": True,
        "expected_facts": [
            "Validation rejects empty files before processing."
        ],
        "expected_evidence": [
            {
                "source_id": "validation-basics-pdf",
                "page": 1,
            }
        ],
    }
    source_index = {
        "validation-basics-pdf": {
            "path": "fixtures/validation_basics.pdf",
        }
    }
    observation = {
        "case_id": "validation-001",
        "answer": "Validation từ chối file rỗng trước khi xử lý.",
        "answer_correct": True,
        "sources": [
            {
                "source": "validation_basics.pdf",
                "page": 1,
            }
        ],
        "faithful": True,
    }

    assert score_answer_observation(
        case,
        observation,
        source_index,
    ) == {
        "answer_correct": True,
        "citation_hit": True,
        "faithful": True,
        "refusal_correct": None,
    }
