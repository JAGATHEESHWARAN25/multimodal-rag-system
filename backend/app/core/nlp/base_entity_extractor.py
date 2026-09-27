from abc import ABC, abstractmethod
from typing import List, Dict

class BaseEntityExtractor(ABC):
    """Abstract interface for entity extraction implementations."""

    @abstractmethod
    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        pass
