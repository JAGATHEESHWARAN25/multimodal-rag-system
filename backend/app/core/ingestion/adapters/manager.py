from typing import Type, Dict, List
import logging
from app.core.ingestion.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

class AdapterManager:
    """
    Registry for document ingestion adapters.
    Routes incoming files to the correct adapter based on MIME type.
    """
    
    _registry: Dict[str, Type[BaseAdapter]] = {}

    @classmethod
    def register_adapter(cls, mime_types: List[str], adapter_class: Type[BaseAdapter]):
        """Registers an adapter for specific MIME types."""
        for mime in mime_types:
            cls._registry[mime] = adapter_class
            logger.info(f"Registered {adapter_class.__name__} for {mime}")

    @classmethod
    def get_adapter(cls, mime_type: str) -> BaseAdapter:
        """Retrieves an instantiated adapter for the given MIME type."""
        adapter_class = cls._registry.get(mime_type)
        if not adapter_class:
            raise ValueError(f"No adapter registered for MIME type: {mime_type}")
        return adapter_class()

    @classmethod
    def list_supported_formats(cls) -> List[str]:
        """Returns a list of all currently supported MIME types."""
        return list(cls._registry.keys())

    @classmethod
    def unregister_adapter(cls, mime_type: str):
        """Removes an adapter from the registry."""
        if mime_type in cls._registry:
            del cls._registry[mime_type]
