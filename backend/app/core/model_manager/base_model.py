import abc
import time
import logging

logger = logging.getLogger(__name__)

class BaseModelInterface(abc.ABC):
    """
    Abstract base class for all AI models managed by the ModelManager.
    Ensures consistent lifecycle management (lazy loading, health checking, offloading).
    """
    
    def __init__(self, model_id: str, is_loaded: bool = False):
        self.model_id = model_id
        self.is_loaded = is_loaded
        self.last_used = 0.0

    @abc.abstractmethod
    def load(self):
        """Loads the model weights into memory. Must be idempotent."""
        pass

    @abc.abstractmethod
    def unload(self):
        """Releases the model weights from memory to free up RAM/VRAM."""
        pass

    @abc.abstractmethod
    def check_health(self) -> bool:
        """Returns True if the model is correctly initialized and reachable."""
        pass

    def mark_used(self):
        """Updates the last used timestamp for LRU memory offloading."""
        self.last_used = time.time()
