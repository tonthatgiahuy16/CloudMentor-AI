from app.rag.cleaner import TextCleaner, UNIVERSITY_HEADER


def test_cleaner_removes_header_and_normalizes_whitespace():
    text = f"{UNIVERSITY_HEADER}\n  Cloud   computing\nlesson "

    assert TextCleaner().clean(text) == "Cloud computing lesson"


def test_cleaner_accepts_empty_text():
    assert TextCleaner().clean("") == ""


def test_cleaner_preserves_line_boundaries_when_requested():
    text = (
        "  first   line \r\n"
        " second\tline\n"
        "\n"
        " third  "
    )

    cleaned = TextCleaner().clean(
        text,
        preserve_line_breaks=True,
    )

    assert cleaned == (
        "first line\n"
        "second line\n"
        "\n"
        "third"
    )
    assert cleaned.count("\n") == 3
