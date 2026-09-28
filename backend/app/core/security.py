from datetime import datetime, timedelta
import os
import jwt
import bcrypt
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Read secret from environment or configuration
# NEVER hardcode in production!
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "DEMO_SECRET_KEY_NEVER_USE_IN_PROD")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours (Extended session expiration)

security = HTTPBearer()

class Role(str, Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    INTELLIGENCE_ANALYST = "INTELLIGENCE_ANALYST"
    DOCUMENT_OFFICER = "DOCUMENT_OFFICER"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"
    AUDITOR = "AUDITOR"
    STANDARD_USER = "STANDARD_USER"

class AccessClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"
    TOP_SECRET = "TOP_SECRET"

class UserContext(BaseModel):
    id: str
    username: str
    role: Role
    
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    # Hash a password for the first time
    # (Using bcrypt, the salt is saved into the hash itself)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserContext:
    payload = decode_access_token(credentials.credentials)
    user_id: str = payload.get("sub")
    username: str = payload.get("username") or user_id
    role: str = payload.get("role")
    
    if user_id is None or role is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    return UserContext(id=user_id, username=username, role=Role(role))

from fastapi import Query

optional_security = HTTPBearer(auto_error=False)

def get_current_user_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    token: Optional[str] = Query(None)
) -> UserContext:
    """Authenticates user via either Authorization Bearer header or token query parameter."""
    raw_token = None
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token
        
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    payload = decode_access_token(raw_token)
    user_id: str = payload.get("sub")
    username: str = payload.get("username") or user_id
    role: str = payload.get("role")
    
    if user_id is None or role is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    return UserContext(id=user_id, username=username, role=Role(role))

def require_roles(allowed_roles: List[Role]):
    def role_checker(current_user: UserContext = Depends(get_current_user_flexible)):
        # Treat AUDITOR as REVIEWER and STANDARD_USER as VIEWER if needed
        user_role = current_user.role
        effective_roles = [user_role]
        if user_role == Role.AUDITOR:
            effective_roles.append(Role.REVIEWER)
        elif user_role == Role.REVIEWER:
            effective_roles.append(Role.AUDITOR)
        elif user_role == Role.STANDARD_USER:
            effective_roles.append(Role.VIEWER)
        elif user_role == Role.VIEWER:
            effective_roles.append(Role.STANDARD_USER)

        if not any(r in allowed_roles for r in effective_roles):
            raise HTTPException(
                status_code=403, 
                detail="The user does not have access to this resource"
            )
        return current_user
    return role_checker

def authorize_document_classification(user: UserContext, document_classification: str):
    """Enforce hierarchical document classification checks."""
    try:
        doc_class = AccessClassification(document_classification)
    except ValueError:
        doc_class = AccessClassification.PUBLIC # Default to lowest if missing
        
    if user.role == Role.SYSTEM_ADMIN:
        return True # Admin accesses everything
        
    if doc_class == AccessClassification.PUBLIC:
        return True
        
    if doc_class == AccessClassification.INTERNAL:
        if user.role in [Role.VIEWER, Role.STANDARD_USER, Role.INTELLIGENCE_ANALYST, Role.DOCUMENT_OFFICER, Role.REVIEWER, Role.AUDITOR]:
            return True
            
    if doc_class == AccessClassification.CONFIDENTIAL:
        if user.role in [Role.INTELLIGENCE_ANALYST, Role.DOCUMENT_OFFICER, Role.REVIEWER, Role.AUDITOR]:
            return True
            
    if doc_class == AccessClassification.SECRET:
        if user.role in [Role.INTELLIGENCE_ANALYST]:
            return True

    if doc_class == AccessClassification.TOP_SECRET:
        if user.role in [Role.INTELLIGENCE_ANALYST]:
            return True
            
    raise HTTPException(
        status_code=403,
        detail=f"User lacks clearance to access {document_classification} documents."
    )

