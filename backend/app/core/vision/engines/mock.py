import uuid
import numpy as np
from app.core.vision.engines.base import BaseVisionEngine
from app.core.vision.result import VisionAnalysisResult, VisionRegion

class MockVisionEngine(BaseVisionEngine):
    """
    Mock engine for testing or CPU-safe fallback without large models.
    """
    def __init__(self, model_id: str = "mock_vlm"):
        super().__init__(model_id=model_id)
        
    def load(self):
        self.is_loaded = True
        
    def unload(self):
        self.is_loaded = False
        
    def check_health(self) -> bool:
        return self.is_loaded
        
    def analyze(self, image: np.ndarray, task: str, asset_id: str, **kwargs) -> VisionAnalysisResult:
        self.mark_used()
        h, w = image.shape[:2]
        
        regions = []
        caption = None
        
        if task == "DOCUMENT_LAYOUT":
            regions = [
                VisionRegion(region_id=str(uuid.uuid4()), label="figure", bbox=[10.0, 10.0, float(w//2), float(h//2)], confidence=0.95),
                VisionRegion(region_id=str(uuid.uuid4()), label="table", bbox=[float(w//2 + 10), 10.0, float(w-10), float(h//2)], confidence=0.92),
                VisionRegion(region_id=str(uuid.uuid4()), label="text", bbox=[10.0, float(h//2 + 10), float(w-10), float(h-10)], confidence=0.99)
            ]
        elif task == "IMAGE_CAPTION":
            caption = "This is a detailed mock description of the visual asset."
            
        return VisionAnalysisResult(
            asset_id=asset_id,
            engine=self.model_id,
            task=task,
            confidence=0.9,
            regions=regions,
            caption=caption,
            raw_output={"mock": True}
        )

    def predict(self, image: np.ndarray, task: str = "DOCUMENT_LAYOUT", **kwargs):
        return self.analyze(image, task=task, asset_id=str(uuid.uuid4()), **kwargs)

