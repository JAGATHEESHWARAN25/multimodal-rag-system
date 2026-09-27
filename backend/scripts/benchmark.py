import time
import os
import psutil
import logging
from pathlib import Path
import json
from app.core.model_manager import model_manager
from app.config import BENCHMARK_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BenchmarkFramework:
    """
    Framework to evaluate VLM and OCR performance on the local machine.
    Measures CPU, RAM, Latency, and saves a report to BENCHMARK_DIR.
    """
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.report = {
            "timestamp": time.time(),
            "models": {}
        }
        
    def _measure_resources(self):
        mem_info = self.process.memory_info()
        return {
            "ram_mb": mem_info.rss / (1024 * 1024),
            "cpu_percent": self.process.cpu_percent(interval=0.1)
        }

    def run_benchmark(self, category: str, model_id: str, sample_image_path: str = None):
        logger.info(f"--- Starting Benchmark: {category}/{model_id} ---")
        
        # 1. Measure Idle State
        idle_resources = self._measure_resources()
        
        # 2. Measure Load Time & Peak RAM
        start_load = time.time()
        model = model_manager.get_model(category, model_id)
        load_time_ms = int((time.time() - start_load) * 1000)
        
        loaded_resources = self._measure_resources()
        ram_delta_mb = loaded_resources["ram_mb"] - idle_resources["ram_mb"]
        
        if not model:
            logger.error(f"Failed to load {model_id} for benchmarking.")
            return
            
        # 3. Measure Inference Latency
        # Use a dummy matrix if no real image provided
        import numpy as np
        image = np.zeros((800, 600, 3), dtype=np.uint8) if not sample_image_path else None
        
        start_infer = time.time()
        result = model.predict(image)
        infer_time_ms = int((time.time() - start_infer) * 1000)
        
        inference_resources = self._measure_resources()
        
        # 4. Cleanup
        model_manager.unload_model(category, model_id)
        
        # 5. Record
        self.report["models"][model_id] = {
            "category": category,
            "load_time_ms": load_time_ms,
            "inference_time_ms": infer_time_ms,
            "ram_consumed_mb": round(ram_delta_mb, 2),
            "peak_ram_mb": round(inference_resources["ram_mb"], 2),
            "cpu_spike_percent": inference_resources["cpu_percent"]
        }
        
        logger.info(f"Benchmark Complete for {model_id}: {self.report['models'][model_id]}")

    def save_report(self):
        report_path = BENCHMARK_DIR / f"benchmark_report_{int(time.time())}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=4)
        logger.info(f"Benchmark report saved to {report_path}")

if __name__ == "__main__":
    benchmark = BenchmarkFramework()
    # Phase 1.5 - Framework built, but actual heavy models are not downloaded yet.
    benchmark.run_benchmark("ocr", "tesseract")
    benchmark.run_benchmark("ocr", "paddleocr")
    benchmark.run_benchmark("vlm", "florence_2")
    benchmark.save_report()
