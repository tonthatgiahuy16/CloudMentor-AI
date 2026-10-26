from evaluation.scoring import has_expected_evidence


def test_matches_txt_evidence_when_chunk_covers_expected_lines():
    expected = [
        {
            "source_id": "storage-basics-txt",
            "line_range": [2, 2],
        }
    ]
    observed = [
        {
            "source_id": "storage-basics-txt",
            "line_range": [1, 3],
        }
    ]

    assert has_expected_evidence(expected, observed)


def test_rejects_txt_evidence_when_chunk_does_not_cover_expected_lines():
    expected = [
        {
            "source_id": "storage-basics-txt",
            "line_range": [2, 2],
        }
    ]
    observed = [
        {
            "source_id": "storage-basics-txt",
            "line_range": [3, 3],
        }
    ]

    assert not has_expected_evidence(expected, observed)


def test_matches_docx_evidence_when_chunk_covers_expected_paragraphs():
    expected = [
        {
            "source_id": "ingestion-basics-docx",
            "paragraph_range": [2, 2],
        }
    ]
    observed = [
        {
            "source_id": "ingestion-basics-docx",
            "paragraph_range": [1, 3],
        }
    ]

    assert has_expected_evidence(expected, observed)


def test_matches_pdf_evidence_on_the_expected_page():
    expected = [
        {
            "source_id": "validation-basics-pdf",
            "page": 1,
        }
    ]

    assert has_expected_evidence(
        expected,
        [
            {
                "source_id": "validation-basics-pdf",
                "page": 1,
            }
        ],
    )

    assert not has_expected_evidence(
        expected,
        [
            {
                "source_id": "validation-basics-pdf",
                "page": 2,
            }
        ],
    )


def test_rejects_evidence_from_a_different_source():
    expected = [
        {
            "source_id": "storage-basics-txt",
            "line_range": [2, 2],
        }
    ]
    observed = [
        {
            "source_id": "another-source",
            "line_range": [1, 3],
        }
    ]

    assert not has_expected_evidence(expected, observed)
