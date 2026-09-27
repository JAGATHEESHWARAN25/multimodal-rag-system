import cv2
import numpy as np
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class QualityReport(BaseModel):
    """Data model representing the results of the image quality analysis and early category estimation."""
    quality_score: float = Field(..., description="Normalized 0.0 to 1.0 IQS")
    estimated_category: str = Field(..., description="Early heuristic category estimate (document, diagram, photograph, unknown)")
    category_confidence: float = Field(..., description="Confidence of the heuristic category estimate")
    metrics: Dict[str, Any] = Field(..., description="Raw metric values")
    recommended_pipeline: List[str] = Field(..., description="OpenCV operations recommended")
    profile_used: str = Field(..., description="Processing profile selected")
    estimated_cost_ms: int = Field(..., description="Estimated computational cost of processing in milliseconds")
    estimated_cpu_cost: str = Field(..., description="High, Medium, or Low CPU impact")

class ImageQualityAnalyzer:
    """
    Independent, decoupled service to analyze a numpy image array.
    Evaluates blur, noise, contrast, resolution, and estimates category via CV heuristics.
    """
    
    @staticmethod
    def _estimate_category(gray: np.ndarray, bgr: np.ndarray = None) -> Tuple[str, float]:
        """Uses lightweight CV heuristics to guess the image type without OCR or VLMs."""
        h, w = gray.shape
        total_pixels = h * w
        
        # 1. White-space ratio (Thresholding to find background)
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        white_pixels = cv2.countNonZero(binary)
        white_ratio = white_pixels / total_pixels
        
        # 2. Edge density (Canny edges)
        edges = cv2.Canny(gray, 100, 200)
        edge_pixels = cv2.countNonZero(edges)
        edge_density = edge_pixels / total_pixels
        
        # 3. Color distribution (if BGR is provided)
        color_variance = 0.0
        if bgr is not None and len(bgr.shape) == 3:
            b, g, r = cv2.split(bgr)
            color_variance = np.var(b) + np.var(g) + np.var(r)
            
        category = "unknown"
        confidence = 0.5
        
        if white_ratio > 0.85 and edge_density < 0.15:
            # Mostly white background, sparse edges
            category = "document"
            confidence = 0.85
        elif white_ratio > 0.70 and 0.15 <= edge_density < 0.35:
            # Lots of edges, mostly white -> likely a dense table or architectural diagram
            category = "diagram"
            confidence = 0.75
        elif white_ratio < 0.20 and color_variance > 10000:
            # Very little white background, high color variance -> likely a photo/screenshot
            category = "photograph"
            confidence = 0.80
        elif 0.20 <= white_ratio <= 0.70 and edge_density > 0.35:
            # High edge density, mixed background -> dense screenshot or detailed diagram
            category = "screenshot"
            confidence = 0.70
            
        return category, confidence

    @staticmethod
    def analyze(image: np.ndarray, profile: str = "Balanced") -> QualityReport:
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Invalid image input for quality analysis.")
            
        metrics = {}
        pipeline = []
        
        h, w = image.shape[:2]
        metrics['resolution'] = [w, h]
        max_dim = max(h, w)
        if max_dim < 800:
            pipeline.append("Upscale")
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        metrics['blur_variance'] = round(float(laplacian_var), 2)
        if laplacian_var < 100:
            pipeline.append("Sharpen")
            
        contrast = gray.std()
        metrics['contrast'] = round(float(contrast), 2)
        if contrast < 40:
            pipeline.append("CLAHE")
            
        brightness = gray.mean()
        metrics['brightness'] = round(float(brightness), 2)
        if brightness > 220 or brightness < 50:
            if "CLAHE" not in pipeline:
                pipeline.append("CLAHE")
                
        snr = float(brightness / (contrast + 1e-5))
        metrics['noise_snr'] = round(snr, 2)
        if snr < 1.5:
            pipeline.append("Denoise")
            
        # Category estimation
        cat, cat_conf = ImageQualityAnalyzer._estimate_category(gray, image if len(image.shape) == 3 else None)
        
        norm_blur = min(1.0, max(0.0, laplacian_var / 500.0))
        norm_contrast = min(1.0, max(0.0, contrast / 100.0))
        norm_snr = min(1.0, max(0.0, snr / 5.0))
        
        iqs = (norm_blur * 0.4) + (norm_contrast * 0.4) + (norm_snr * 0.2)
        
        if profile == "Fast":
            pipeline = [op for op in pipeline if op not in ["Denoise", "Upscale"]]
            
        # Cost Estimation (Rough baseline)
        cost_ms = 45 # Base quality check cost
        if "Upscale" in pipeline: cost_ms += 100
        if "CLAHE" in pipeline: cost_ms += 80
        if "Denoise" in pipeline: cost_ms += 150
        
        cpu_cost = "Low"
        if cost_ms > 200: cpu_cost = "Medium"
        if cost_ms > 350: cpu_cost = "High"
            
        return QualityReport(
            quality_score=round(float(iqs), 2),
            estimated_category=cat,
            category_confidence=cat_conf,
            metrics=metrics,
            recommended_pipeline=pipeline,
            profile_used=profile,
            estimated_cost_ms=cost_ms,
            estimated_cpu_cost=cpu_cost
        )
