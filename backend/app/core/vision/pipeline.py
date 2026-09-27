import logging
import uuid
import numpy as np
from typing import Dict, Any, List, Tuple
from app.models.schema import KnowledgeObject, RelationshipEdge
from app.core.model_manager import model_manager
from app.core.cache.fingerprint import DocumentFingerprinter
from app.core.vision.table_parser import TableParser
from app.core.vision.chart_parser import ChartParser
from app.core.vision.diagram_parser import DiagramParser

logger = logging.getLogger(__name__)

class VisionPipeline:
    """
    Orchestrates the Vision Intelligence Layer.
    Processes visual assets to detect regions and extract structural understanding.
    """
    
    def __init__(self, mock_vlm: bool = False):
        self.engine_id = "mock_vlm" if mock_vlm else "florence_2"
        self.table_parser = TableParser()
        self.chart_parser = ChartParser()
        self.diagram_parser = DiagramParser()
        
    def process_visual_asset(self, image: np.ndarray, parent_document_id: str, parent_page_id: str, page_number: int) -> Tuple[List[KnowledgeObject], List[RelationshipEdge]]:
        """
        Takes an image asset (like a page or extracted image) and runs the vision pipeline.
        Returns a tuple of (KnowledgeObjects, RelationshipEdges).
        """
        blocks = []
        relationships = []
        
        # Get Vision Engine
        vlm = model_manager.get_model("vlm", self.engine_id)
        if not vlm:
            logger.error(f"Vision engine '{self.engine_id}' not found.")
            return [], []
            
        # 1. Layout Analysis
        asset_id = str(uuid.uuid4())
        layout_cache_key = DocumentFingerprinter.generate_vision_cache_key(image.tobytes(), self.engine_id, "DOCUMENT_LAYOUT")
        cached_layout = DocumentFingerprinter.check_vision_cache(layout_cache_key)
        
        if cached_layout:
            # We must reconstruct the pydantic model from dict
            from app.core.vision.result import VisionAnalysisResult
            layout_result = VisionAnalysisResult(**cached_layout)
        else:
            layout_result = vlm.analyze(image, task="DOCUMENT_LAYOUT", asset_id=asset_id)
            DocumentFingerprinter.cache_vision_result(layout_cache_key, parent_document_id, self.engine_id, "DOCUMENT_LAYOUT", layout_result.model_dump())
        
        for region in layout_result.regions:
            label = region.label
            bbox = region.bbox
            confidence = region.confidence
            
            # Crop image for specific parsers (mocked for now)
            # x0, y0, x1, y1 = [int(v) for v in bbox]
            # cropped_img = image[y0:y1, x0:x1]
            cropped_img = image # using full image for mock
            
            base_metadata = {"bbox": bbox, "page_num": page_number}
            ko_id = region.region_id
            
            if label == "table":
                table_data = self.table_parser.parse(cropped_img, base_metadata)
                
                # Main Table Object
                blocks.append(KnowledgeObject(
                    knowledge_object_id=ko_id,
                    parent_document_id=parent_document_id,
                    parent_object_id=parent_page_id,
                    page_number=page_number,
                    block_type="table",
                    content=f"Table with {table_data['rows']} rows and {table_data['columns']} columns",
                    engine_used="florence-2",
                    confidence=confidence if confidence is not None else 1.0,
                    bounding_box=bbox,
                    metadata=base_metadata
                ))
                
                # Add relationship to page
                relationships.append(RelationshipEdge(
                    source_id=ko_id,
                    target_id=parent_page_id,
                    relationship_type="CHILD_OF"
                ))
                
                # Add cells as children of the table
                for cell in table_data["cells"]:
                    cell_ko_id = str(uuid.uuid4())
                    blocks.append(KnowledgeObject(
                        knowledge_object_id=cell_ko_id,
                        parent_document_id=parent_document_id,
                        parent_object_id=ko_id,
                        page_number=page_number,
                        block_type="table_cell",
                        content=cell["content"],
                        engine_used="florence-2",
                        confidence=confidence if confidence is not None else 1.0,
                        bounding_box=cell["bbox"],
                        metadata={"row": cell["row"], "col": cell["col"]}
                    ))
                    relationships.append(RelationshipEdge(
                        source_id=cell_ko_id,
                        target_id=ko_id,
                        relationship_type="CHILD_OF"
                    ))
                    
            elif label == "figure" or label == "chart":
                caption_cache_key = DocumentFingerprinter.generate_vision_cache_key(cropped_img.tobytes(), self.engine_id, "IMAGE_CAPTION")
                cached_caption = DocumentFingerprinter.check_vision_cache(caption_cache_key)
                
                if cached_caption:
                    from app.core.vision.result import VisionAnalysisResult
                    caption_res = VisionAnalysisResult(**cached_caption)
                else:
                    caption_res = vlm.analyze(cropped_img, task="IMAGE_CAPTION", asset_id=asset_id)
                    DocumentFingerprinter.cache_vision_result(caption_cache_key, parent_document_id, self.engine_id, "IMAGE_CAPTION", caption_res.model_dump())
                
                caption = caption_res.caption or ""
                chart_data = self.chart_parser.parse(cropped_img, caption, base_metadata)
                
                blocks.append(KnowledgeObject(
                    knowledge_object_id=ko_id,
                    parent_document_id=parent_document_id,
                    parent_object_id=parent_page_id,
                    page_number=page_number,
                    block_type="chart",
                    content=caption,
                    caption=caption,
                    engine_used=self.engine_id,
                    confidence=confidence if confidence is not None else 1.0,
                    bounding_box=bbox,
                    metadata=chart_data
                ))
                relationships.append(RelationshipEdge(
                    source_id=ko_id,
                    target_id=parent_page_id,
                    relationship_type="CHILD_OF"
                ))
                
            elif label == "diagram":
                caption_cache_key = DocumentFingerprinter.generate_vision_cache_key(cropped_img.tobytes(), self.engine_id, "IMAGE_CAPTION")
                cached_caption = DocumentFingerprinter.check_vision_cache(caption_cache_key)
                
                if cached_caption:
                    from app.core.vision.result import VisionAnalysisResult
                    caption_res = VisionAnalysisResult(**cached_caption)
                else:
                    caption_res = vlm.analyze(cropped_img, task="IMAGE_CAPTION", asset_id=asset_id)
                    DocumentFingerprinter.cache_vision_result(caption_cache_key, parent_document_id, self.engine_id, "IMAGE_CAPTION", caption_res.model_dump())
                
                caption = caption_res.caption or ""
                diagram_data = self.diagram_parser.parse(cropped_img, caption, base_metadata)
                
                blocks.append(KnowledgeObject(
                    knowledge_object_id=ko_id,
                    parent_document_id=parent_document_id,
                    parent_object_id=parent_page_id,
                    page_number=page_number,
                    block_type="diagram",
                    content=caption,
                    caption=caption,
                    engine_used=self.engine_id,
                    confidence=confidence if confidence is not None else 1.0,
                    bounding_box=bbox,
                    metadata={"caption": caption}
                ))
                relationships.append(RelationshipEdge(
                    source_id=ko_id,
                    target_id=parent_page_id,
                    relationship_type="CHILD_OF"
                ))
                
                # Add diagram nodes and edges as separate KOs and RelationshipEdges
                node_id_map = {}
                for node in diagram_data.get("nodes", []):
                    n_id = str(uuid.uuid4())
                    node_id_map[node["id"]] = n_id
                    blocks.append(KnowledgeObject(
                        knowledge_object_id=n_id,
                        parent_document_id=parent_document_id,
                        parent_object_id=ko_id,
                        page_number=page_number,
                        block_type="diagram_node",
                        content=node["label"],
                        engine_used=self.engine_id,
                        confidence=confidence if confidence is not None else 1.0,
                        metadata={"node_type": node.get("type", "process")}
                    ))
                    relationships.append(RelationshipEdge(
                        source_id=n_id,
                        target_id=ko_id,
                        relationship_type="CHILD_OF"
                    ))
                    
                for edge in diagram_data.get("edges", []):
                    src = node_id_map.get(edge["source"])
                    tgt = node_id_map.get(edge["target"])
                    if src and tgt:
                        relationships.append(RelationshipEdge(
                            source_id=src,
                            target_id=tgt,
                            relationship_type="CONNECTED_TO"
                        ))
                
            else:
                # General Text/Fallback
                caption_cache_key = DocumentFingerprinter.generate_vision_cache_key(cropped_img.tobytes(), self.engine_id, "IMAGE_CAPTION")
                cached_caption = DocumentFingerprinter.check_vision_cache(caption_cache_key)
                
                if cached_caption:
                    from app.core.vision.result import VisionAnalysisResult
                    caption_res = VisionAnalysisResult(**cached_caption)
                else:
                    caption_res = vlm.analyze(cropped_img, task="IMAGE_CAPTION", asset_id=asset_id)
                    DocumentFingerprinter.cache_vision_result(caption_cache_key, parent_document_id, self.engine_id, "IMAGE_CAPTION", caption_res.model_dump())
                
                caption = caption_res.caption or ""
                
                blocks.append(KnowledgeObject(
                    knowledge_object_id=ko_id,
                    parent_document_id=parent_document_id,
                    parent_object_id=parent_page_id,
                    page_number=page_number,
                    block_type=label,
                    content=caption,
                    engine_used=self.engine_id,
                    confidence=confidence if confidence is not None else 1.0,
                    bounding_box=bbox,
                    metadata=base_metadata
                ))
                relationships.append(RelationshipEdge(
                    source_id=ko_id,
                    target_id=parent_page_id,
                    relationship_type="CHILD_OF"
                ))
                
        return blocks, relationships
