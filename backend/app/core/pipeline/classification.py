import logging
from typing import Dict, Any
from app.core.pipeline.quality_check import QualityReport

logger = logging.getLogger(__name__)

class DocumentClassifier:
    """
    Consumes the QualityReport to finalize document routing classification.
    Prevents recalculating image properties by relying on the pre-computed 
    heuristics from the Image Quality Analyzer.
    """
    
    @staticmethod
    def classify(quality_report: QualityReport) -> Dict[str, Any]:
        """
        Finalizes the classification category and determines pipeline routing.
        """
        
        category = quality_report.estimated_category
        confidence = quality_report.category_confidence
        
        # Override heuristics if necessary based on other metrics
        # For example, if resolution is tiny, it might be a thumbnail or cropped screenshot
        w, h = quality_report.metrics.get('resolution', [0, 0])
        if max(w, h) < 300 and category == "document":
            category = "unknown_fragment"
            confidence = 0.50
            
        routing_decision = "standard_pipeline"
        
        # Determine Routing based on Category & Quality
        if category in ["document", "table"] and quality_report.quality_score > 0.85:
            routing_decision = "fast_ocr_path" # Route to Tesseract
            
        elif category in ["document", "table"] and quality_report.quality_score <= 0.85:
            routing_decision = "robust_ocr_path" # Route to PaddleOCR
            
        elif category in ["diagram", "photograph", "screenshot"]:
            routing_decision = "vlm_analysis_path" # Requires VLM layout analysis
            
        else:
            routing_decision = "fallback_path"
            
        return {
            "final_category": category,
            "classification_confidence": confidence,
            "routing_decision": routing_decision
        }
