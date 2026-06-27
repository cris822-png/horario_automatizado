from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    from app.models.models import Empleado

    payload = decode_token(token)
    emp_id: Optional[int] = payload.get("sub")
    if emp_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin sub")
    result = await db.execute(select(Empleado).where(Empleado.id == int(emp_id)))
    empleado = result.scalar_one_or_none()
    if not empleado or not empleado.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empleado no encontrado")
    return empleado


async def require_coordinador(current_user=Depends(get_current_user)):
    from app.models.models import RolEmpleado
    if current_user.rol not in (RolEmpleado.coordinador, RolEmpleado.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol coordinador")
    return current_user
