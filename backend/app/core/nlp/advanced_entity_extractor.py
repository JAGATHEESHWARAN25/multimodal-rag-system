import re
import logging
from typing import List, Dict
from app.core.nlp.base_entity_extractor import BaseEntityExtractor
from app.core.nlp.entity_extractor import RuleBasedEntityExtractor

logger = logging.getLogger(__name__)

class AdvancedLocalEntityExtractor(BaseEntityExtractor):
    """Enhanced offline entity extractor supporting multi-pattern regex, gazetteers, and classification markings with automatic fallback."""

    CLASSIFICATION_MARKINGS = re.compile(
        r'\b(?:TOP SECRET|SECRET|RESTRICTED|CONFIDENTIAL|OFFICIAL USE ONLY|UNCLASSIFIED)\b',
        re.IGNORECASE
    )
    LOCATION_PATTERN = re.compile(
        r'\b(?:New Delhi|Mumbai|Bangalore|Kolkata|Chennai|Washington|London|Berlin|Tokyo|Beijing|Singapore)\b',
        re.IGNORECASE
    )
    GOVT_DEPT_PATTERN = re.compile(
        r'\b(?:Ministry of \w+|Department of \w+|National Investigation Agency|NTRO|IB|RAW|CBI|DRDO|ISRO)\b',
        re.IGNORECASE
    )

    def __init__(self):
        self.fallback_extractor = RuleBasedEntityExtractor()

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        try:
            # First run base rule-based extraction
            entities = self.fallback_extractor.extract(text)

            # Add Classification Markings
            for match in self.CLASSIFICATION_MARKINGS.finditer(text):
                entities.append({"type": "CLASSIFICATION_MARKING", "value": match.group().upper()})

            # Add Locations
            for match in self.LOCATION_PATTERN.finditer(text):
                entities.append({"type": "LOCATION", "value": match.group().strip()})

            # Add Govt Departments
            for match in self.GOVT_DEPT_PATTERN.finditer(text):
                entities.append({"type": "ORGANIZATION", "value": match.group().strip()})

            # Deduplicate
            seen = set()
            unique_entities = []
            for e in entities:
                identifier = (e["type"], e["value"].lower())
                if identifier not in seen:
                    seen.add(identifier)
                    unique_entities.append(e)

            return unique_entities

        except Exception as e:
            logger.warning(f"Advanced entity extraction failed: {e}. Falling back to RuleBasedEntityExtractor.")
            return self.fallback_extractor.extract(text)
