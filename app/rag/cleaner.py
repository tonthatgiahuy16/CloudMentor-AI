import re


class TextCleaner:


    def clean(self, text:str):

        # Remove multiple spaces
        text = re.sub(
            r'\s+',
            ' ',
            text
        )


        # Remove university header
        text = text.replace(
            "TRƯỜNG ĐẠI HỌC GIAO THÔNG VẬN TẢI THÀNH PHỐ HỒ CHÍ MINH",
            ""
        )


        return text.strip()