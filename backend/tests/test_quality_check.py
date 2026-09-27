import pytest
import numpy as np
import cv2
from app.core.pipeline.quality_check import ImageQualityAnalyzer

def create_synthetic_document():
    # Mostly white background, sparse text (edges)
    img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    cv2.putText(img, "This is a clean document.", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    return img

def create_synthetic_photograph():
    # High color variance, low white space
    return np.random.randint(0, 255, (1000, 800, 3), dtype=np.uint8)

def create_synthetic_diagram():
    # High white space, but lots of geometric edges
    img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    for i in range(20):
        cv2.rectangle(img, (i*30, i*30), (i*30+100, i*30+100), (0,0,0), 2)
    return img

def test_document_classification():
    img = create_synthetic_document()
    report = ImageQualityAnalyzer.analyze(img)
    assert report.estimated_category == "document"
    assert report.quality_score > 0.5  # High enough for synthetic image

def test_photograph_classification():
    img = create_synthetic_photograph()
    report = ImageQualityAnalyzer.analyze(img)
    assert report.estimated_category == "photograph"

def test_diagram_classification():
    img = create_synthetic_diagram()
    report = ImageQualityAnalyzer.analyze(img)
    assert report.estimated_category in ["diagram", "document"]

def test_degraded_quality_triggers_pipeline():
    # Blurry image
    img = create_synthetic_document()
    blurry = cv2.GaussianBlur(img, (15, 15), 0)
    report = ImageQualityAnalyzer.analyze(blurry)
    assert "Sharpen" in report.recommended_pipeline
    assert report.quality_score < 0.6
    
def test_estimated_costs():
    img = create_synthetic_document()
    report = ImageQualityAnalyzer.analyze(img)
    assert report.estimated_cost_ms >= 45
    assert report.estimated_cpu_cost in ["Low", "Medium", "High"]
