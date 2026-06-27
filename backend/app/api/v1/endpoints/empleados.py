from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_coordinador
from app.db.session import get_db
from app.models.models import Empleado, RolEmpleado
from app.core.security import get_password_hash
from app.schemas.schemas import EmpleadoCreate, EmpleadoOut, EmpleadoUpdate

router = APIRouter(prefix="/empleados", tags=["empleados"])


@router.get("/", response_model=list[EmpleadoOut])
async def list_empleados(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Empleado).where(
            Empleado.empresa_id == current_user.empresa_id,
            Empleado.activo == True,
        )
    )
    return result.scalars().all()


@router.post("/", response_model=EmpleadoOut, status_code=status.HTTP_201_CREATED)
async def create_empleado(
    data: EmpleadoCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    payload = data.model_dump()
    payload["password_hash"] = get_password_hash(payload.pop("password"))
    payload["empresa_id"] = current_user.empresa_id
    emp = Empleado(**payload)
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


@router.get("/{id}", response_model=EmpleadoOut)
async def get_empleado(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp = await db.get(Empleado, id)
    if not emp or emp.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return emp


@router.patch("/{id}", response_model=EmpleadoOut)
async def update_empleado(
    id: int,
    data: EmpleadoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp = await db.get(Empleado, id)
    if not emp or emp.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    # Trabajador solo puede actualizar su propio fcm_token
    is_coordinador = current_user.rol in (RolEmpleado.coordinador, RolEmpleado.admin)
    if not is_coordinador:
        if current_user.id != id:
            raise HTTPException(status_code=403, detail="Sin permiso")
        allowed = {"fcm_token"}
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if k in allowed}
    else:
        updates = data.model_dump(exclude_unset=True)

    for k, v in updates.items():
        setattr(emp, k, v)
    await db.commit()
    await db.refresh(emp)
    return emp


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_empleado(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    emp = await db.get(Empleado, id)
    if not emp or emp.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    emp.activo = False  # soft delete
    await db.commit()
