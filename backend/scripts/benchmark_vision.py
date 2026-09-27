import os
import sys
import time
import psutil
import logging
import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.model_manager import model_manager
from app.core.vision.engines.florence2 import Florence2Engine
from app.core.vision.pipeline import VisionPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def measure_ram():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def run_benchmark():
    logger.info("Initializing Vision Benchmark...")
    start_ram = measure_ram()
    logger.info(f"Initial RAM: {start_ram:.2f} MB")
    
    # 1. Cold Load
    start_time = time.time()
    model_manager.register_model_class("vlm", "florence_2", Florence2Engine, {"model_id": "florence_2"})
    # Initialize pipeline
    pipeline = VisionPipeline(mock_vlm=False)
    # Force load by getting model
    engine = model_manager.get_model("vlm", "florence_2")
    cold_load_time = time.time() - start_time
    loaded_ram = measure_ram()
    logger.info(f"Cold Load Latency: {cold_load_time:.2f} seconds")
    logger.info(f"RAM after Load: {loaded_ram:.2f} MB (Peak Delta: {loaded_ram - start_ram:.2f} MB)")
    
    # 2. Benchmark on test set
    images_dir = "data/benchmarks"
    if not os.path.exists(images_dir):
        logger.error("No benchmark images found!")
        return

    images = [f for f in os.listdir(images_dir) if f.endswith('.png') or f.endswith('.jpg')]
    
    for i, img_name in enumerate(images):
        img_path = os.path.join(images_dir, img_name)
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        logger.info(f"--- Benchmarking: {img_name} ---")
        
        # Warm Inference (or First inference if i=0)
        start_time = time.time()
        blocks, relationships = pipeline.process_visual_asset(
            image=img,
            parent_document_id=f"doc_{i}",
            parent_page_id=f"page_{i}",
            page_number=1
        )
        inference_time = time.time() - start_time
        logger.info(f"Inference Latency: {inference_time:.2f} seconds")
        logger.info(f"Blocks generated: {len(blocks)}, Rels: {len(relationships)}")
        
        # Cache Hit Validation
        start_time = time.time()
        blocks_cached, rels_cached = pipeline.process_visual_asset(
            image=img,
            parent_document_id=f"doc_{i}",
            parent_page_id=f"page_{i}",
            page_number=1
        )
        cache_time = time.time() - start_time
        logger.info(f"Cache Hit Latency: {cache_time:.2f} seconds")
        assert len(blocks) == len(blocks_cached), "Cache output differs from model output"
        
        logger.info(f"RAM during inference: {measure_ram():.2f} MB")
        print("\n")

if __name__ == "__main__":
    run_benchmark()
