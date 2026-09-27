import logging
import uuid
from typing import Optional, Dict, Any
from app.models.database import db_manager
from app.core.security import UserContext

logger = logging.getLogger(__name__)

class AuditLogger:
    @staticmethod
    def log(
        event_type: str,
        action: str,
        user: Optional[UserContext] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "SUCCESS",
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Safely records an audit event without crashing the main thread on failure.
        """
        # Ensure we never log sensitive data like tokens or passwords
        safe_details = "{}"
        if details:
            # Strip potential sensitive fields just in case
            safe_dict = {k: v for k, v in details.items() if "password" not in k.lower() and "token" not in k.lower() and "secret" not in k.lower()}
            import json
            try:
                safe_details = json.dumps(safe_dict)
            except Exception:
                safe_details = '{"error": "unserializable details"}'
                
        user_id = user.id if user else None
        username = user.username if user else None
        role = user.role.value if (user and hasattr(user.role, 'value')) else (user.role if user else None)
        
        if not request_id:
            request_id = str(uuid.uuid4())
            
        try:
            db_manager.log_audit_event(
                event_type=event_type,
                action=action,
                user_id=user_id,
                username=username,
                role=role,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                ip_address=ip_address,
                request_id=request_id,
                details=safe_details
            )
        except Exception as e:
            # Audit logging must not crash the primary application flow
            logger.error(f"Failed to write audit log: {str(e)} | Event: {event_type} | Action: {action}")
