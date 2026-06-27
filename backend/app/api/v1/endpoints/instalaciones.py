from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_coordinador
from app.db.session import get_db
from app.models.models import Empresa, Instalacion
from app.schemas.schemas import InstalacionCreate, InstalacionOut, InstalacionUpdate

router = APIRouter(prefix="/instalaciones", tags=["instalaciones"])


@router.get("/", response_model=list[InstalacionOut])
async def list_instalaciones(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Instalacion).where(Instalacion.empresa_id == current_user.empresa_id)
    )
    return result.scalars().all()


@router.post("/", response_model=InstalacionOut, status_code=status.HTTP_201_CREATED)
async def create_instalacion(
    data: InstalacionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    inst = Instalacion(**data.model_dump(), empresa_id=current_user.empresa_id)
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return inst


@router.get("/{id}", response_model=InstalacionOut)
async def get_instalacion(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    inst = await db.get(Instalacion, id)
    if not inst or inst.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Instalación no encontrada")
    return inst


@router.patch("/{id}", response_model=InstalacionOut)
async def update_instalacion(
    id: int,
    data: InstalacionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    inst = await db.get(Instalacion, id)
    if not inst or inst.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Instalación no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(inst, k, v)
    await db.commit()
    await db.refresh(inst)
    return inst


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instalacion(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    inst = await db.get(Instalacion, id)
    if not inst or inst.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Instalación no encontrada")
    await db.delete(inst)
    await db.commit()
