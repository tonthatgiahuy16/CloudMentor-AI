from docx import Document

from evaluation.chunking_ablation import build_variants


def test_build_variants_compares_full_document_with_target_paragraph(
    tmp_path,
):
    source_path = tmp_path / "ingestion.docx"
    document = Document()
    document.add_paragraph("The pipeline reads source documents.")
    document.add_paragraph("The transform cleans text before chunking.")
    document.add_paragraph("Each chunk retains a source reference.")
    document.save(source_path)

    variants = build_variants(source_path, target_paragraph=3)

    assert variants == [
        {
            "name": "baseline_full_document",
            "paragraph_range": [1, 3],
            "text": (
                "The pipeline reads source documents.\n"
                "The transform cleans text before chunking.\n"
                "Each chunk retains a source reference."
            ),
        },
        {
            "name": "isolated_target_paragraph",
            "paragraph_range": [3, 3],
            "text": "Each chunk retains a source reference.",
        },
    ]
