import logging
from typing import Dict, Any, Callable
from datetime import datetime
from app.models.database import db_manager

logger = logging.getLogger(__name__)

class EventBus:
    """
    Internal event bus for the processing pipeline.
    Logs events to SQLite tracking database automatically.
    """
    
    _subscribers = []

    @classmethod
    def subscribe(cls, callback: Callable[[str, Dict[str, Any]], None]):
        """Registers a listener for internal events."""
        cls._subscribers.append(callback)

    @classmethod
    def emit(cls, event_name: str, payload: Dict[str, Any]):
        """
        Broadcasts an event and automatically logs it to processing_history if applicable.
        """
        logger.info(f"EVENT: {event_name} | Doc: {payload.get('document_id', 'unknown')}")
        
        # Fire subscribers (synchronous for Phase 1.5)
        for sub in cls._subscribers:
            try:
                sub(event_name, payload)
            except Exception as e:
                logger.error(f"Subscriber error on {event_name}: {e}")
                
        # Auto-log core pipeline events to SQLite processing_history
        doc_id = payload.get("document_id")
        if doc_id:
            # We construct a fake end_time for discrete events. For timed events, modules will call log_processing_event directly.
            # But the EventBus can handle status milestones.
            db_manager.log_processing_event(
                document_id=doc_id,
                stage=event_name,
                start_time=datetime.now(),
                end_time=datetime.now(),
                model_used=payload.get("engine", "System"),
                status=payload.get("status", "Completed"),
                trace_log=str(payload)
            )

# Convenience instance
event_bus = EventBus()
