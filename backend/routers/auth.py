from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from models.schemas import LoginRequest, LoginResponse
from services.database import (
    get_user_by_username, save_token, get_user_by_token as db_get_user_by_token,
    save_user, delete_token, refresh_token as db_refresh_token,
)
import uuid
import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash. Also supports legacy plaintext for migration."""
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    # Legacy plaintext fallback
    return password == hashed

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "student"
    display_name: str = ""
    class_id: str = ""


def get_user_by_token(token: str) -> dict | None:
    return db_get_user_by_token(token)


@router.post("/register", response_model=LoginResponse)
def register(req: RegisterRequest):
    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少3个字符")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")
    user_id = str(uuid.uuid4())
    ok = save_user(user_id, req.username, hash_password(req.password), req.role or "student",
                   req.display_name, req.class_id)
    if not ok:
        raise HTTPException(status_code=409, detail="用户名已存在")
    token = str(uuid.uuid4())
    save_token(token, user_id)
    return LoginResponse(
        token=token,
        user_id=user_id,
        username=req.username,
        role=req.role or "student",
    )


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if req.role and user["role"] != req.role:
        raise HTTPException(status_code=403, detail="角色不匹配，请选择正确的登录身份")

    token = str(uuid.uuid4())
    save_token(token, user["user_id"])

    return LoginResponse(
        token=token,
        user_id=user["user_id"],
        username=user["username"],
        role=user["role"],
    )


@router.post("/refresh")
def refresh(request: Request):
    """Refresh an expiring token. Returns a new token with extended expiration."""
    auth = request.headers.get("Authorization", "")
    old_token = auth.replace("Bearer ", "").strip()
    if not old_token:
        raise HTTPException(status_code=401, detail="未提供 Token")
    result = db_refresh_token(old_token)
    if not result:
        raise HTTPException(status_code=401, detail="Token 无效或已过期，请重新登录")
    new_token, user = result
    return {
        "token": new_token,
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
    }


@router.post("/logout")
def logout(request: Request):
    """Delete the current token (logout)."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    if token:
        delete_token(token)
    return {"ok": True}
