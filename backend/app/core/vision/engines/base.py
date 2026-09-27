import abc
import numpy as np
from PIL import Image
from app.core.vision.interface import VisionEngine

class BaseVisionEngine(VisionEngine, abc.ABC):
    """
    Base class for Vision Intelligence Engines.
    Provides utility methods common to VLMs (like NumPy -> PIL conversion).
    """
    
    def _numpy_to_pil(self, image: np.ndarray) -> Image.Image:
        if image.dtype != np.uint8:
            image = (image * 255).astype(np.uint8)
        if len(image.shape) == 2:
            return Image.fromarray(image, mode='L').convert("RGB")
        elif len(image.shape) == 3:
            if image.shape[2] == 4:
                return Image.fromarray(image, mode='RGBA').convert("RGB")
            return Image.fromarray(image, mode='RGB')
        return Image.fromarray(image)
