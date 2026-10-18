import re


UNIVERSITY_HEADER = (
    "TRƯỜNG ĐẠI HỌC GIAO THÔNG VẬN TẢI THÀNH PHỐ HỒ CHÍ MINH"
)


class TextCleaner:
    def clean(
        self,
        text: str,
        *,
        preserve_line_breaks: bool = False,
    ) -> str:
        """
        Normalize whitespace while optionally preserving
        source line boundaries.
        """

        normalized_newlines = (
            (text or "")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )

        if preserve_line_breaks:
            cleaned_lines = []

            for line in normalized_newlines.split(
                "\n"
            ):
                cleaned_line = re.sub(
                    r"[^\S\r\n]+",
                    " ",
                    line,
                )
                cleaned_line = (
                    cleaned_line.replace(
                        UNIVERSITY_HEADER,
                        "",
                    )
                )
                cleaned_lines.append(
                    cleaned_line.strip()
                )

            return "\n".join(cleaned_lines)

        normalized = re.sub(
            r"\s+",
            " ",
            normalized_newlines,
        )
        normalized = normalized.replace(
            UNIVERSITY_HEADER,
            "",
        )

        return normalized.strip()
