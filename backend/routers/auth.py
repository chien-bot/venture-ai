from fastapi import APIRouter, HTTPException
from models.schemas import LoginRequest, LoginResponse
from services.database import get_user_by_username, save_token, get_user_by_token as db_get_user_by_token
import uuid

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_user_by_token(token: str) -> dict | None:
    return db_get_user_by_token(token)


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
