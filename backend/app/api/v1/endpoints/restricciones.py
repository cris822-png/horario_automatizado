from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_coordinador
from app.db.session import get_db
from app.models.models import Empleado, Restriccion, RolEmpleado
from app.schemas.schemas import RestriccionCreate, RestriccionOut, RestriccionUpdate

router = APIRouter(prefix="/restricciones", tags=["restricciones"])


@router.get("/", response_model=list[RestriccionOut])
async def list_restricciones(
    empleado_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Trabajador solo ve las suyas
    is_coordinador = current_user.rol in (RolEmpleado.coordinador, RolEmpleado.admin)
    target_id = empleado_id if is_coordinador else current_user.id

    q = (
        select(Restriccion)
        .join(Empleado, Restriccion.empleado_id == Empleado.id)
        .where(Empleado.empresa_id == current_user.empresa_id)
    )
    if target_id:
        q = q.where(Restriccion.empleado_id == target_id)
    return (await db.execute(q)).scalars().all()


@router.post("/", response_model=RestriccionOut, status_code=status.HTTP_201_CREATED)
async def create_restriccion(
    data: RestriccionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp = await db.get(Empleado, data.empleado_id)
    if not emp or emp.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    # Auto-aprobada si la crea el coordinador
    is_coordinador = current_user.rol in (RolEmpleado.coordinador, RolEmpleado.admin)
    r = Restriccion(**data.model_dump(), aprobada=is_coordinador)
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@router.patch("/{id}/aprobar", response_model=RestriccionOut)
async def aprobar_restriccion(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    r = await db.get(Restriccion, id)
    if not r:
        raise HTTPException(status_code=404, detail="Restricción no encontrada")
    emp = await db.get(Empleado, r.empleado_id)
    if emp.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=403, detail="Restricción de otra empresa")
    r.aprobada = True
    await db.commit()
    await db.refresh(r)
    return r
