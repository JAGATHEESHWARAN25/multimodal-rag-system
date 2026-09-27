import re
from typing import List, Dict
from app.core.nlp.base_entity_extractor import BaseEntityExtractor

class RuleBasedEntityExtractor(BaseEntityExtractor):
    """Lightweight regex-based entity extraction as a zero-dependency baseline."""

    @classmethod
    def extract_entities(cls, text: str) -> List[Dict[str, str]]:
        instance = cls()
        return instance.extract(text)

    def extract(self, text: str) -> List[Dict[str, str]]:
        entities = []
        
        for match in self.DATE_PATTERN.finditer(text):
            entities.append({"type": "DATE", "value": match.group().strip()})
            
        for match in self.EMAIL_PATTERN.finditer(text):
            entities.append({"type": "EMAIL", "value": match.group().strip()})
            
        for match in self.PHONE_PATTERN.finditer(text):
            entities.append({"type": "PHONE", "value": match.group().strip()})
            
        for match in self.MONEY_PATTERN.finditer(text):
            entities.append({"type": "MONEY", "value": match.group().strip()})
            
        for match in self.DOC_ID_PATTERN.finditer(text):
            entities.append({"type": "DOCUMENT_ID", "value": match.group().strip()})
            
        org_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|LLC|Corp|Ministry|Department|Agency|Bureau|NTRO))\b')
        for match in org_pattern.finditer(text):
            entities.append({"type": "ORGANIZATION", "value": match.group().strip()})
            
        seen = set()
        unique_entities = []
        for e in entities:
            identifier = (e["type"], e["value"].lower())
            if identifier not in seen:
                seen.add(identifier)
                unique_entities.append(e)
                
        return unique_entities

    DATE_PATTERN = re.compile(r'\b(?:\d{1,2}[-/th|st|nd|rd\s]*)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/,\s]*\d{2,4}\b', re.IGNORECASE)
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    MONEY_PATTERN = re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:million|billion|trillion))?', re.IGNORECASE)
    DOC_ID_PATTERN = re.compile(r'\b(?:DOC|ID|REF)[-:]?\s*\d+[A-Z]*\b', re.IGNORECASE)

EntityExtractor = RuleBasedEntityExtractor

