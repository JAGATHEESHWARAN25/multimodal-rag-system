import logging
import time
import numpy as np
from typing import Dict, Any, List
from app.core.model_manager.base_model import BaseModelInterface
import pytesseract
from app.config import TESSERACT_PATH

logger = logging.getLogger(__name__)

class TesseractOCRModel(BaseModelInterface):
    """Wrapper for Tesseract OCR within the Model Manager."""
    
    def __init__(self):
        super().__init__(model_id="tesseract", is_loaded=False)
        self.engine = None
        
    def load(self):
        if not self.is_loaded:
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
            self.engine = pytesseract
            self.is_loaded = True
            logger.info("Tesseract loaded.")
            
    def unload(self):
        if self.is_loaded:
            self.engine = None
            self.is_loaded = False
            logger.info("Tesseract unloaded.")
            
    def check_health(self) -> bool:
        return self.is_loaded and self.engine is not None
        
    def predict(self, image) -> Dict[str, Any]:
        """Extracts text and calculates a rough confidence score."""
        self.mark_used()
        start = time.time()
        try:
            # Get verbose data for confidence scores
            data = self.engine.image_to_data(image, output_type=pytesseract.Output.DICT)
            text = " ".join([word for word in data['text'] if word.strip()])
            
            # Calculate average confidence of valid words
            confidences = [int(conf) for conf in data['conf'] if int(conf) != -1]
            avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
            
            return {
                "text": text,
                "confidence": round(avg_conf, 4),
                "engine": self.model_id,
                "execution_time_ms": int((time.time() - start) * 1000),
                "error": None
            }
        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "engine": self.model_id,
                "execution_time_ms": int((time.time() - start) * 1000),
                "error": str(e)
            }


class PaddleOCRModel(BaseModelInterface):
    """Wrapper for PaddleOCR within the Model Manager."""
    
    def __init__(self):
        super().__init__(model_id="paddleocr", is_loaded=False)
        self.engine = None
        
    def load(self):
        if not self.is_loaded:
            try:
                from paddleocr import PaddleOCR
                # Using english lang and disabling angle classification for speed
                self.engine = PaddleOCR(use_angle_cls=False, lang='en')
                self.is_loaded = True
                logger.info("PaddleOCR loaded.")
            except AttributeError as e:
                if "pkgutil" in str(e):
                    logger.error("PaddleOCR is incompatible with Python 3.12 due to pkg_resources issues. Downgrade Python or use Tesseract.")
                    self.engine = None
                else:
                    raise
            except ImportError:
                logger.error("PaddleOCR library not installed.")
                self.is_loaded = False
            
    def unload(self):
        if self.is_loaded:
            self.engine = None
            self.is_loaded = False
            logger.info("PaddleOCR unloaded.")
            
    def check_health(self) -> bool:
        return self.is_loaded and self.engine is not None
        
    def predict(self, image: np.ndarray) -> Dict[str, Any]:
        if not self.engine:
            return {"text": "", "confidence": 0.0, "error": "PaddleOCR not loaded"}
        self.mark_used()
        start = time.time()
        try:
            result = self.engine.ocr(image, cls=True)
            text_blocks = []
            confidences = []
            
            if result and result[0]:
                for line in result[0]:
                    # line format: [[box], (text, confidence)]
                    text_blocks.append(line[1][0])
                    confidences.append(line[1][1])
                    
            text = "\n".join(text_blocks)
            avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.0
            
            return {
                "text": text,
                "confidence": round(avg_conf, 4),
                "engine": self.model_id,
                "execution_time_ms": int((time.time() - start) * 1000),
                "error": None
            }
        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "engine": self.model_id,
                "execution_time_ms": int((time.time() - start) * 1000),
                "error": str(e)
            }
