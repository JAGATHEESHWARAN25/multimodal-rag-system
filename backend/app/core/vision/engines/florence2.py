import logging
import os
import time
import uuid
import numpy as np
from typing import Dict, Any, List
import torch
from app.config import VISION_MODEL_PATH, VISION_DEVICE
from app.core.vision.engines.base import BaseVisionEngine
from app.core.vision.result import VisionAnalysisResult, VisionRegion

logger = logging.getLogger(__name__)

class Florence2Engine(BaseVisionEngine):
    """
    Real implementation of the Florence-2 Vision Engine.
    Operates completely offline, respects ResourceManager limits, and maps tasks cleanly.
    """
    def __init__(self, model_id: str = "florence_2"):
        super().__init__(model_id=model_id)
        self.model_path = VISION_MODEL_PATH
        self.device = self._determine_device()
        self.model = None
        self.processor = None
        
    def _determine_device(self) -> str:
        if VISION_DEVICE == "auto":
            if torch.cuda.is_available():
                return "cuda"
            # Mac / CPU fallback
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        return VISION_DEVICE

    def load(self):
        if self.is_loaded:
            return
            
        logger.info(f"Loading Florence-2 from {self.model_path} onto {self.device}...")
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            # Use local_files_only=True to prevent silent internet downloads in production
            # if we expect it to be downloaded already. 
            # We will try loading normally first but catch connection errors.
            self.processor = AutoProcessor.from_pretrained(
                self.model_path, 
                trust_remote_code=True,
                local_files_only=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path, 
                trust_remote_code=True,
                local_files_only=True
            ).to(self.device).eval()
            self.is_loaded = True
            logger.info("Florence-2 loaded successfully.")
        except Exception as e:
            error_msg = f"Failed to load Florence-2 from {self.model_path}. Please ensure model weights are downloaded locally. Error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    def unload(self):
        if self.is_loaded:
            self.model = None
            self.processor = None
            if self.device == "cuda":
                torch.cuda.empty_cache()
            self.is_loaded = False
            logger.info(f"VLM '{self.model_id}' unloaded.")

    def check_health(self) -> bool:
        return self.is_loaded
        
    def analyze(self, image: np.ndarray, task: str, asset_id: str, **kwargs) -> VisionAnalysisResult:
        if not self.is_loaded:
            self.load()
            
        self.mark_used()
        pil_image = self._numpy_to_pil(image)
        width, height = pil_image.size
        
        task_prompt = ""
        if task == "DOCUMENT_LAYOUT":
            task_prompt = "<OD>"
        elif task == "IMAGE_CAPTION":
            task_prompt = "<MORE_DETAILED_CAPTION>"
        elif task == "OCR_ASSIST":
            task_prompt = "<OCR>"
        elif task == "DENSE_REGION_CAPTION":
            task_prompt = "<DENSE_REGION_CAPTION>"
        else:
            raise ValueError(f"UnsupportedVisionTaskError: Task {task} not supported by Florence-2.")
            
        start_time = time.time()
        
        inputs = self.processor(text=task_prompt, images=pil_image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                num_beams=3
            )
            
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = self.processor.post_process_generation(generated_text, task=task_prompt, image_size=(width, height))
        
        end_time = time.time()
        logger.debug(f"Florence-2 task {task} took {end_time - start_time:.2f}s")
        
        regions = []
        caption = None
        
        # Parse the structured output
        if task_prompt in parsed_answer:
            answer_content = parsed_answer[task_prompt]
            
            if isinstance(answer_content, dict) and "bboxes" in answer_content:
                # OD or DENSE_REGION_CAPTION
                bboxes = answer_content["bboxes"]
                labels = answer_content["labels"]
                
                for bbox, label in zip(bboxes, labels):
                    # Florence-2 OD output bounding boxes are [x0, y0, x1, y1]
                    regions.append(VisionRegion(
                        region_id=str(uuid.uuid4()),
                        label=label.lower(),
                        bbox=bbox,
                        confidence=None, # Florence-2 base generation doesn't easily expose exact confidences for boxes natively without logits parsing
                    ))
            elif isinstance(answer_content, str):
                caption = answer_content
                
        return VisionAnalysisResult(
            asset_id=asset_id,
            engine=self.model_id,
            task=task,
            confidence=None,
            regions=regions,
            caption=caption,
            raw_output=parsed_answer
        )

    def predict(self, image: np.ndarray, task: str = "DOCUMENT_LAYOUT", **kwargs) -> Any:
        return self.analyze(image, task=task, asset_id=str(uuid.uuid4()), **kwargs)

