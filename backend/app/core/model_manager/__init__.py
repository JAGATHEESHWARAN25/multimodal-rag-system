import logging
from typing import Dict, Any, Type, Optional
from app.core.model_manager.base_model import BaseModelInterface
from app.core.model_manager.ocr_models import TesseractOCRModel, PaddleOCRModel

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Centralized registry for all AI models.
    Implements lazy loading, model retrieval, and fallback routing.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._registry = {} # Dict of loaded/available model instances
            cls._instance._model_classes = {} # Registry for lazy loading
            cls._instance._register_defaults()
        return cls._instance
        
    def _register_defaults(self):
        """Registers default Phase 1 models."""
        self.register_model_class("ocr", "tesseract", TesseractOCRModel)
        self.register_model_class("ocr", "paddleocr", PaddleOCRModel)
        
    def register_model_class(self, category: str, model_id: str, model_cls: Type[BaseModelInterface], default_kwargs: dict = None):
        """Registers a model class for lazy loading."""
        if category not in self._model_classes:
            self._model_classes[category] = {}
        self._model_classes[category][model_id] = {
            "class": model_cls,
            "kwargs": default_kwargs or {}
        }
        
    def get_model(self, category: str, model_id: str) -> Optional[BaseModelInterface]:
        """
        Retrieves a model by category and ID. Loads it if it isn't loaded yet.
        """
        if category in self._registry and model_id in self._registry[category]:
            model = self._registry[category][model_id]
            if model.is_loaded:
                model.mark_used()
                return model

        # Dynamically register vision engines on first request to avoid circular imports
        if category == "vlm":
            if category not in self._model_classes:
                self._model_classes[category] = {}
            if model_id == "florence_2" and "florence_2" not in self._model_classes[category]:
                try:
                    from app.core.vision.engines.florence2 import Florence2Engine
                    self.register_model_class("vlm", "florence_2", Florence2Engine, {"model_id": "florence_2"})
                except Exception as e:
                    logger.warning(f"Failed to import Florence2Engine: {e}")
            elif model_id == "mock_vlm" and "mock_vlm" not in self._model_classes[category]:
                try:
                    from app.core.vision.engines.mock import MockVisionEngine
                    self.register_model_class("vlm", "mock_vlm", MockVisionEngine, {"model_id": "mock_vlm"})
                except Exception as e:
                    logger.warning(f"Failed to import MockVisionEngine: {e}")
                
        if category in self._model_classes and model_id in self._model_classes[category]:
            logger.info(f"Lazy loading model: {category}/{model_id}")
            cfg = self._model_classes[category][model_id]
            try:
                model_instance = cfg["class"](**cfg["kwargs"])
                model_instance.load()
                
                if category not in self._registry:
                    self._registry[category] = {}
                self._registry[category][model_id] = model_instance
                
                model_instance.mark_used()
                return model_instance
            except Exception as e:
                logger.warning(f"Model {model_id} failed to load: {e}")
                if category == "vlm" and model_id != "mock_vlm":
                    logger.info("Falling back to mock_vlm")
                    return self.get_model("vlm", "mock_vlm")
                return None
            
        logger.error(f"Model {model_id} in category {category} is not registered.")
        return None
        
    def unload_model(self, category: str, model_id: str):
        if category in self._registry and model_id in self._registry[category]:
            model = self._registry[category][model_id]
            if model.is_loaded:
                logger.info(f"Unloading model: {category}/{model_id}")
                model.unload()
                
    def unload_all(self):
        for cat, models in self._registry.items():
            for m_id, model in models.items():
                if model.is_loaded:
                    model.unload()

# Singleton instance
model_manager = ModelManager()
