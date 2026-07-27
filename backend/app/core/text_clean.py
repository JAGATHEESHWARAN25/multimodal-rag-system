import re

class OCRTextCleaner:
    """Provides regex-based text cleaning filters to normalize OCR layout noise."""

    @staticmethod
    def reassemble_hyphenated_words(text: str) -> str:
        """Stitches back together words that were split across lines with a hyphen.
        
        Example: "de- \n velopment" -> "development"
        """
        # Match word chars followed by hyphen, newline, optional whitespace, and the rest of the word
        pattern = r"(\w+)-\s*\n\s*(\w+)"
        return re.sub(pattern, r"\1\2", text)

    @staticmethod
    def remove_junk_characters(text: str) -> str:
        """Strips solitary noise symbols (like lone vertical pipes or underscores)
        while protecting valid textual characters.
        """
        # Matches lone noise characters surrounded by whitespace or string boundaries
        noise_pattern = r"(^|\s)[\|_\\~^•\-*](\s|$)"
        cleaned = re.sub(noise_pattern, r"\1\2", text)
        
        # Strip non-printable unicode artifacts, retaining standard ASCII (range 32 to 126)
        cleaned = "".join(ch for ch in cleaned if (32 <= ord(ch) <= 126) or ch in ("\n", "\r"))
        
        return cleaned

    @staticmethod
    def normalize_whitespaces(text: str) -> str:
        """Normalizes horizontal spaces and vertical line breaks.
        
        Applies individual line-by-line whitespace stripping.
        """
        # Strip leading and trailing spaces on each individual line
        text = re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        
        # Replace multiple tabs/spaces with a single space
        text = re.sub(r"[ \t]+", " ", text)
        
        # Limit consecutive newlines (3 or more) to exactly 2 newlines (preserves paragraph separation)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()

    @classmethod
    def clean(cls, text: str) -> str:
        """Runs the complete sequence of text cleaning filters."""
        if not text:
            return ""
        cleaned = cls.reassemble_hyphenated_words(text)
        cleaned = cls.remove_junk_characters(cleaned)
        cleaned = cls.normalize_whitespaces(cleaned)
        return cleaned
