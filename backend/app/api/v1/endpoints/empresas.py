# Stub — empresas endpoint (admin scope, minimal for now)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_coordinador
from app.db.session import get_db
from app.models.models import Empresa
from app.schemas.schemas import EmpresaOut

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get("/me", response_model=EmpresaOut)
async def get_mi_empresa(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    empresa = await db.get(Empresa, current_user.empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa
