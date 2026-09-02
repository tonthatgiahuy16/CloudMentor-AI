import re


UNIVERSITY_HEADER = (
    "TRƯỜNG ĐẠI HỌC GIAO THÔNG VẬN TẢI THÀNH PHỐ HỒ CHÍ MINH"
)


class TextCleaner:
    def clean(self, text: str) -> str:
        """Normalize whitespace and remove the repeated university header."""

        normalized = re.sub(r"\s+", " ", text or "")
        normalized = normalized.replace(UNIVERSITY_HEADER, "")
        return normalized.strip()
