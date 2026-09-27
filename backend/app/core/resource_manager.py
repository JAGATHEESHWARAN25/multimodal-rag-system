import psutil
import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResourceManager:
    """
    Manages system resources to prevent RAM exhaustion and coordinate streaming.
    Provides logic for temporary cache management and stream-vs-memory decisions.
    """
    
    def __init__(self, temp_cache_dir: str = ".cache/temp_assets"):
        self.temp_cache_dir = Path(temp_cache_dir)
        self.temp_cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_threshold_percent = 85.0 # Max RAM usage before forcing streams
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Returns current CPU and RAM usage."""
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        return {
            "ram_percent": ram.percent,
            "ram_available_gb": ram.available / (1024**3),
            "cpu_percent": cpu
        }
        
    def should_stream(self, file_size_bytes: int, estimated_expansion_factor: int = 10) -> bool:
        """
        Determines whether a document should be processed fully in memory or streamed.
        Small documents go to memory, large documents or high RAM usage triggers streaming.
        """
        metrics = self.get_system_metrics()
        
        # If system is already under heavy load, force stream
        if metrics["ram_percent"] > self.memory_threshold_percent:
            return True
            
        estimated_ram_needed = file_size_bytes * estimated_expansion_factor
        
        # If estimated RAM needed exceeds 20% of available RAM, stream it
        if estimated_ram_needed > (psutil.virtual_memory().available * 0.2):
            return True
            
        return False

    def get_batch_size(self, estimated_page_size_mb: float = 5.0) -> int:
        """
        Dynamically calculates how many pages to process in a batch.
        Batch Size = 1 (Maximum Memory Safety)
        Batch Size = 5 (Balanced Performance)
        Batch Size = 10 (Higher Throughput)
        """
        metrics = self.get_system_metrics()
        ram_available_mb = metrics["ram_available_gb"] * 1024
        
        # If memory is critical (< 15% available) or overall usage > 85%, use safe batch
        if metrics["ram_percent"] > self.memory_threshold_percent or ram_available_mb < 500:
            return 1
            
        # Balanced: If we have moderate memory (e.g., > 1GB available)
        if ram_available_mb > 2048:
            return 10
        elif ram_available_mb > 1024:
            return 5
            
        return 1

    def get_temp_asset_path(self, document_id: str, asset_name: str) -> Path:
        """Returns a path for a temporary extracted asset (e.g., an image from a PDF)."""
        doc_dir = self.temp_cache_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir / asset_name

    def clear_temp_assets(self, document_id: str):
        """Cleans up temporary assets for a document once processing is finished."""
        doc_dir = self.temp_cache_dir / document_id
        if doc_dir.exists():
            for file in doc_dir.iterdir():
                if file.is_file():
                    try:
                        file.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete temp asset {file}: {e}")
            try:
                doc_dir.rmdir()
            except Exception as e:
                logger.error(f"Failed to delete temp dir {doc_dir}: {e}")

# Global instance
resource_manager = ResourceManager()
