from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.models.database import db_manager
from app.core.security import verify_password, create_access_token, get_current_user, UserContext

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str
    role: str

from app.core.audit import AuditLogger

@router.get("/setup-status")
def get_setup_status():
    with db_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
    return {"is_first_time": count == 0}

class InitialSetupRequest(BaseModel):
    username: str
    password: str

@router.post("/initial-setup", response_model=TokenResponse)
def initial_setup(request: InitialSetupRequest):
    with db_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        if count > 0:
            raise HTTPException(status_code=400, detail="Initial setup already completed.")
            
    from app.core.security import get_password_hash
    import uuid
    user_id = str(uuid.uuid4())
    hashed = get_password_hash(request.password)
    
    db_manager.create_user(user_id, request.username, hashed, "USER")
    
    token_data = {
        "sub": user_id,
        "username": request.username,
        "role": "USER"
    }
    access_token = create_access_token(data=token_data)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user_id,
        username=request.username,
        role="USER"
    )

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    with db_manager._get_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (request.username,))
        user = cursor.fetchone()
        
    if not user:
        # Log failed login attempt
        AuditLogger.log(
            event_type="AUTHENTICATION",
            action="LOGIN_FAILED", 
            status="FAILED", 
            details={"reason": "Unknown username", "attempted_username": request.username}
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    if not verify_password(request.password, user["password_hash"]):
        AuditLogger.log(
            event_type="AUTHENTICATION",
            action="LOGIN_FAILED", 
            user=UserContext(id=user["id"], username=user["username"], role=user["role"]),
            status="FAILED", 
            details={"reason": "Incorrect password"}
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    # Generate token
    token_data = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"]
    }
    
    access_token = create_access_token(data=token_data)
    
    AuditLogger.log(
        event_type="AUTHENTICATION",
        action="LOGIN", 
        user=UserContext(id=user["id"], username=user["username"], role=user["role"]),
        status="SUCCESS", 
        details={"message": "User logged in"}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user["id"],
        username=user["username"],
        role=user["role"]
    )

@router.get("/me", response_model=UserContext)
def read_users_me(current_user: UserContext = Depends(get_current_user)):
    return current_user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
def change_password(request: ChangePasswordRequest, current_user: UserContext = Depends(get_current_user)):
    with db_manager._get_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, role FROM users WHERE id = ?", (current_user.id,))
        user = cursor.fetchone()
        
    if not user or not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
        
    from app.core.security import get_password_hash
    new_hash = get_password_hash(request.new_password)
    db_manager.update_user_password(current_user.id, new_hash)
    
    AuditLogger.log(
        event_type="USER_MANAGEMENT",
        action="PASSWORD_CHANGED",
        user=current_user,
        resource_type="user",
        resource_id=current_user.id,
        status="SUCCESS",
        details={"message": f"Password changed for {current_user.username}"}
    )
    return {"status": "success", "message": "Password updated successfully"}

# Helper to fetch sqlite row as dict
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

from pydantic import BaseModel
from app.core.security import require_roles, Role, UserContext

from pydantic import BaseModel
from app.core.security import require_roles, Role, UserContext

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

@router.get("/users")
def get_all_users(current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN]))):
    users = db_manager.get_all_users()
    return {"users": [{"id": u["id"], "username": u["username"], "role": u["role"], "created_at": u["created_at"]} for u in users]}

@router.post("/users")
def create_new_user(user: UserCreate, current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN]))):
    from app.core.security import get_password_hash
    import uuid
    user_id = str(uuid.uuid4())
    hashed = get_password_hash(user.password)
    try:
        db_manager.create_user(user_id, user.username, hashed, user.role)
        AuditLogger.log(
            event_type="USER_MANAGEMENT",
            action="USER_CREATED",
            user=current_user,
            resource_type="user",
            resource_id=user_id,
            status="SUCCESS",
            details={"username": user.username, "role": user.role}
        )
        return {"status": "success", "message": "User created"}
    except Exception as e:
        from fastapi import HTTPException
        AuditLogger.log(
            event_type="USER_MANAGEMENT",
            action="USER_CREATE_FAILED",
            user=current_user,
            resource_type="user",
            status="FAILED",
            details={"username": user.username, "error": str(e)}
        )
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{user_id}")
def delete_user(user_id: str, current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN]))):
    if user_id == current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db_manager.delete_user(user_id)
    AuditLogger.log(
        event_type="USER_MANAGEMENT",
        action="USER_DELETED",
        user=current_user,
        resource_type="user",
        resource_id=user_id,
        status="SUCCESS",
        details={"deleted_user_id": user_id}
    )
    return {"status": "success", "message": "User deleted"}

from fastapi import UploadFile, File

@router.post("/users/bulk")
async def create_users_bulk(file: UploadFile = File(...), current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN]))):
    import csv
    import uuid
    from io import StringIO
    from app.core.security import get_password_hash
    
    content = await file.read()
    text = content.decode('utf-8')
    reader = csv.DictReader(StringIO(text))
    
    count = 0
    for row in reader:
        username = row.get('username')
        password = row.get('password')
        role = row.get('role', 'VIEWER')
        
        if not username or not password:
            continue
            
        user_id = str(uuid.uuid4())
        hashed = get_password_hash(password)
        try:
            db_manager.create_user(user_id, username, hashed, role)
            count += 1
        except Exception as e:
            pass # Skip duplicates or errors
            
    AuditLogger.log(
        event_type="USER_MANAGEMENT",
        action="USERS_BULK_IMPORTED",
        user=current_user,
        resource_type="user",
        status="SUCCESS",
        details={"imported_count": count}
    )

    return {"status": "success", "count": count, "message": f"Successfully imported {count} users"}

class GenerateRequest(BaseModel):
    count: int
    role: str

@router.post("/users/generate")
def auto_generate_users(req: GenerateRequest, current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN]))):
    import uuid
    from app.core.security import get_password_hash
    
    count = req.count
    target_role = req.role
    
    generated = 0
    for i in range(count):
        uid = str(uuid.uuid4())
        short_id = uid[:6]
        username = f"user_{short_id}"
        password = f"pass_{short_id}"
        
        hashed = get_password_hash(password)
        try:
            db_manager.create_user(uid, username, hashed, target_role)
            generated += 1
        except Exception:
            pass
            
    AuditLogger.log(
        event_type="USER_MANAGEMENT",
        action="USERS_AUTO_GENERATED",
        user=current_user,
        resource_type="user",
        status="SUCCESS",
        details={"generated_count": generated, "role": target_role}
    )

    return {"status": "success", "count": generated, "message": f"Successfully generated {generated} users"}
