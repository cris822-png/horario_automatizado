from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_coordinador
from app.db.session import get_db
from app.models.models import (
    CambioTurno, Empleado, EstadoSustitucion, EstadoTurno,
    Instalacion, Turno,
)
from app.schemas.schemas import (
    CambioTurnoOut, CandidatoSustitucion, ProponerSustitutoIn,
    ReportarBajaIn, ResponderSustitucionIn,
)
from app.services.motor_restricciones import MotorSustituciones
from app.services.notificaciones import notificacion_service

router = APIRouter(prefix="/sustituciones", tags=["sustituciones"])


@router.post("/reportar-baja", response_model=CambioTurnoOut, status_code=status.HTTP_201_CREATED)
async def reportar_baja(
    data: ReportarBajaIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    turno = await db.get(Turno, data.turno_id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    turno.estado = EstadoTurno.descubierto
    cambio = CambioTurno(
        turno_id=data.turno_id,
        solicitante_id=current_user.id,
        motivo_baja=data.motivo_baja,
    )
    db.add(cambio)
    await db.commit()
    await db.refresh(cambio)
    return cambio


@router.get("/{turno_id}/candidatos", response_model=list[CandidatoSustitucion])
async def get_candidatos(
    turno_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    turno = await db.get(Turno, turno_id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    result = await db.execute(
        select(Empleado).where(
            Empleado.empresa_id == current_user.empresa_id,
            Empleado.activo == True,
            Empleado.id != turno.empleado_id,
        )
    )
    candidatos = result.scalars().all()
    motor = MotorSustituciones(db)
    return await motor.puntuar_candidatos(turno, candidatos)


@router.post("/{cambio_id}/proponer", response_model=CambioTurnoOut)
async def proponer_sustituto(
    cambio_id: int,
    data: ProponerSustitutoIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    cambio = await db.get(CambioTurno, cambio_id)
    if not cambio or cambio.estado != EstadoSustitucion.pendiente:
        raise HTTPException(status_code=404, detail="Cambio no encontrado o ya resuelto")

    receptor = await db.get(Empleado, data.receptor_id)
    if not receptor:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    # ponytail: INSERT-only table, create new cambio row for the proposal
    nuevo_cambio = CambioTurno(
        turno_id=cambio.turno_id,
        solicitante_id=current_user.id,
        receptor_id=data.receptor_id,
        motivo_baja=cambio.motivo_baja,
        notas_coordinador=f"Propuesto por coordinador {current_user.id}",
    )
    db.add(nuevo_cambio)
    await db.commit()
    await db.refresh(nuevo_cambio)
    await notificacion_service.notificar_solicitud_sustitucion(receptor, cambio.turno_id)
    return nuevo_cambio


@router.post("/{cambio_id}/responder", response_model=CambioTurnoOut)
async def responder_sustitucion(
    cambio_id: int,
    data: ResponderSustitucionIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cambio = await db.get(CambioTurno, cambio_id)
    if not cambio or cambio.receptor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Cambio no encontrado")
    if cambio.estado != EstadoSustitucion.pendiente:
        raise HTTPException(status_code=409, detail="El cambio ya fue resuelto")

    ahora = datetime.now(timezone.utc)
    # ponytail: append-only — resolve by inserting a new resolved row; update receptor on turno
    cambio.estado = EstadoSustitucion.aceptada if data.acepta else EstadoSustitucion.rechazada
    cambio.resuelto_en = ahora

    if data.acepta:
        turno = await db.get(Turno, cambio.turno_id)
        if turno:
            turno.empleado_id = current_user.id
            turno.estado = EstadoTurno.cubierto

    await db.commit()
    await db.refresh(cambio)
    return cambio


@router.get("/historial", response_model=list[CambioTurnoOut])
async def historial(
    instalacion_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    q = (
        select(CambioTurno)
        .join(Turno, CambioTurno.turno_id == Turno.id)
        .join(Instalacion, Turno.instalacion_id == Instalacion.id)
        .where(Instalacion.empresa_id == current_user.empresa_id)
        .order_by(CambioTurno.propuesto_en.desc())
    )
    if instalacion_id:
        q = q.where(Turno.instalacion_id == instalacion_id)
    return (await db.execute(q)).scalars().all()
