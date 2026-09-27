import abc
import numpy as np
from typing import Dict, Any, Optional
from app.core.model_manager.base_model import BaseModelInterface
from app.core.vision.result import VisionAnalysisResult

class VisionEngine(BaseModelInterface, abc.ABC):
    """
    Abstract interface for Vision Intelligence Engines.
    Extends BaseModelInterface so it can be managed by the ModelManager.
    """
    
    def __init__(self, model_id: str):
        super().__init__(model_id=model_id, is_loaded=False)
        
    @abc.abstractmethod
    def analyze(self, image: np.ndarray, task: str, asset_id: str, **kwargs) -> VisionAnalysisResult:
        """
        Performs the specified task on the image.
        Supported tasks generally include:
        - DOCUMENT_LAYOUT
        - IMAGE_CAPTION
        - OCR_ASSIST
        """
        pass
