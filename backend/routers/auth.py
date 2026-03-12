from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.schemas import LoginRequest, LoginResponse
from services.database import get_user_by_username, save_token, get_user_by_token as db_get_user_by_token, save_user
import uuid

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
    ok = save_user(user_id, req.username, req.password, req.role or "student",
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
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user["role"] != req.role:
        raise HTTPException(status_code=403, detail="角色不匹配")

    token = str(uuid.uuid4())
    save_token(token, user["user_id"])

    return LoginResponse(
        token=token,
        user_id=user["user_id"],
        username=user["username"],
        role=user["role"],
    )
