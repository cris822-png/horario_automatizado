from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, create_access_token, get_current_user
from app.db.session import get_db
from app.models.models import Empleado
from app.schemas.schemas import Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Empleado).where(Empleado.email == form.username))
    empleado = result.scalar_one_or_none()
    if not empleado or not verify_password(form.password, empleado.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    if not empleado.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta desactivada")
    token = create_access_token({"sub": str(empleado.id), "rol": empleado.rol.value, "empresa_id": empleado.empresa_id})
    return Token(access_token=token)


@router.get("/me")
async def me(current_user: Empleado = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "rol": current_user.rol, "empresa_id": current_user.empresa_id}
