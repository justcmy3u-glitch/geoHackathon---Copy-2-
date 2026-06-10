import re

class Validator:
    @staticmethod
    def extract_citations(text: str) -> list[str]:
        """
        Extracts citations in the format [doc_id:page]
        Supports cyrillic and hyphens as per user request.
        """
        # [([^\]]+):(\d+)] -> matches [anything:digits]
        matches = re.findall(r'\[([^\]]+):(\d+)\]', text)
        return [f"[{m[0]}:{m[1]}]" for m in matches]
        
    @staticmethod
    def validate_citations(text: str, valid_citations: list[str]) -> bool:
        """
        Checks if the generated text hallucinates citations not in the context.
        """
        found = Validator.extract_citations(text)
        for c in found:
            if c not in valid_citations:
                return False
        return True
