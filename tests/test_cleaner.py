from app.rag.cleaner import TextCleaner, UNIVERSITY_HEADER


def test_cleaner_removes_header_and_normalizes_whitespace():
    text = f"{UNIVERSITY_HEADER}\n  Cloud   computing\nlesson "

    assert TextCleaner().clean(text) == "Cloud computing lesson"


def test_cleaner_accepts_empty_text():
    assert TextCleaner().clean("") == ""
