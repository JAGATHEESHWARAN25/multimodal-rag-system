import os
import sys
from transformers import AutoProcessor, AutoModelForCausalLM
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..") # So it can find dummy flash_attn in backend/

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_model():
    model_id = "microsoft/Florence-2-base"
    logger.info(f"Downloading {model_id} to local huggingface cache...")
    try:
        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
        logger.info(f"Successfully downloaded {model_id}")
    except Exception as e:
        logger.error(f"Failed to download model: {e}")

if __name__ == "__main__":
    download_model()
