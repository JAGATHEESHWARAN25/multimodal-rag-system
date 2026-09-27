from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class VisionRegion(BaseModel):
    region_id: str
    label: str  # e.g., 'table', 'chart', 'figure', 'text'
    bbox: List[float]  # [x0, y0, x1, y1]
    confidence: Optional[float] = None
    text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VisionAnalysisResult(BaseModel):
    asset_id: str
    engine: str
    task: str
    confidence: Optional[float] = None
    regions: List[VisionRegion] = Field(default_factory=list)
    caption: Optional[str] = None
    raw_output: Any = None
