from datetime import datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, require_coordinador
from app.db.session import get_db
from app.models.models import Empleado, Instalacion, Turno, EstadoTurno
from app.schemas.schemas import (
    ResumenCuadro, TurnoCreate, TurnoOut, TurnoUpdate, ValidacionTurno,
)
from app.services.motor_restricciones import MotorValidacion

router = APIRouter(prefix="/turnos", tags=["turnos"])


def _assert_instalacion_pertenece(inst: Instalacion, empresa_id: int):
    if inst.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Instalación de otra empresa")


@router.get("/resumen", response_model=ResumenCuadro)
async def get_resumen(
    instalacion_id: int,
    mes: int,
    anio: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    inst = await db.get(Instalacion, instalacion_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instalación no encontrada")
    _assert_instalacion_pertenece(inst, current_user.empresa_id)

    inicio = datetime(anio, mes, 1)
    fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)

    q = select(Turno).where(
        Turno.instalacion_id == instalacion_id,
        Turno.fecha >= inicio,
        Turno.fecha < fin,
    ).options(selectinload(Turno.empleado))
    turnos = (await db.execute(q)).scalars().all()

    conteo = {e.value: 0 for e in EstadoTurno}
    horas_emp: dict[int, float] = {}
    for t in turnos:
        conteo[t.estado.value] += 1
        if t.empleado_id:
            h = (t.hora_fin.hour * 60 + t.hora_fin.minute - t.hora_inicio.hour * 60 - t.hora_inicio.minute) / 60
            horas_emp[t.empleado_id] = horas_emp.get(t.empleado_id, 0) + h

    return ResumenCuadro(
        total=len(turnos),
        descubiertos=conteo["descubierto"],
        programados=conteo["programado"],
        confirmados=conteo["confirmado"],
        completados=conteo["completado"],
        cancelados=conteo["cancelado"],
        horas_por_empleado=horas_emp,
    )


@router.get("/", response_model=list[TurnoOut])
async def list_turnos(
    instalacion_id: int,
    mes: int,
    anio: int,
    solo_descubiertos: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    inst = await db.get(Instalacion, instalacion_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instalación no encontrada")
    _assert_instalacion_pertenece(inst, current_user.empresa_id)

    inicio = datetime(anio, mes, 1)
    fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)

    q = select(Turno).where(
        Turno.instalacion_id == instalacion_id,
        Turno.fecha >= inicio,
        Turno.fecha < fin,
    ).options(selectinload(Turno.empleado))
    if solo_descubiertos:
        q = q.where(Turno.estado == EstadoTurno.descubierto)
    return (await db.execute(q)).scalars().all()


@router.post("/validar", response_model=ValidacionTurno)
async def validar_turno(
    data: TurnoCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    if not data.empleado_id:
        return ValidacionTurno(valido=True, advertencias=["Sin empleado asignado — turno quedará descubierto"])
    motor = MotorValidacion(db)
    return await motor.validar(
        empleado_id=data.empleado_id,
        instalacion_id=data.instalacion_id,
        fecha=data.fecha,
        hora_inicio=data.hora_inicio,
        hora_fin=data.hora_fin,
        zona=data.zona,
    )


@router.post("/", response_model=TurnoOut, status_code=status.HTTP_201_CREATED)
async def create_turno(
    data: TurnoCreate,
    forzar: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    inst = await db.get(Instalacion, data.instalacion_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instalación no encontrada")
    _assert_instalacion_pertenece(inst, current_user.empresa_id)

    estado = EstadoTurno.programado
    if data.empleado_id:
        motor = MotorValidacion(db)
        val = await motor.validar(
            empleado_id=data.empleado_id,
            instalacion_id=data.instalacion_id,
            fecha=data.fecha,
            hora_inicio=data.hora_inicio,
            hora_fin=data.hora_fin,
            zona=data.zona,
        )
        if not val.valido and not forzar:
            raise HTTPException(status_code=422, detail={"errores": val.errores, "advertencias": val.advertencias})
    else:
        estado = EstadoTurno.descubierto

    h_inicio = time(*map(int, data.hora_inicio.split(":")))
    h_fin = time(*map(int, data.hora_fin.split(":")))
    turno = Turno(
        instalacion_id=data.instalacion_id,
        empleado_id=data.empleado_id,
        zona=data.zona,
        fecha=data.fecha,
        hora_inicio=h_inicio,
        hora_fin=h_fin,
        estado=estado,
        notas=data.notas,
        creado_por_id=current_user.id,
    )
    db.add(turno)
    await db.commit()
    await db.refresh(turno)
    return turno


@router.patch("/{id}", response_model=TurnoOut)
async def update_turno(
    id: int,
    data: TurnoUpdate,
    forzar: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    turno = await db.get(Turno, id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    inst = await db.get(Instalacion, turno.instalacion_id)
    _assert_instalacion_pertenece(inst, current_user.empresa_id)

    updates = data.model_dump(exclude_unset=True)
    # Revalidar si cambia empleado o zona
    if ("empleado_id" in updates or "zona" in updates) and (updates.get("empleado_id") or turno.empleado_id):
        emp_id = updates.get("empleado_id", turno.empleado_id)
        if emp_id:
            motor = MotorValidacion(db)
            val = await motor.validar(
                empleado_id=emp_id,
                instalacion_id=turno.instalacion_id,
                fecha=updates.get("fecha", turno.fecha),
                hora_inicio=updates.get("hora_inicio", turno.hora_inicio.strftime("%H:%M")),
                hora_fin=updates.get("hora_fin", turno.hora_fin.strftime("%H:%M")),
                zona=updates.get("zona", turno.zona),
                excluir_turno_id=id,
            )
            if not val.valido and not forzar:
                raise HTTPException(status_code=422, detail={"errores": val.errores})

    for k, v in updates.items():
        if k == "hora_inicio":
            setattr(turno, k, time(*map(int, v.split(":"))))
        elif k == "hora_fin":
            setattr(turno, k, time(*map(int, v.split(":"))))
        else:
            setattr(turno, k, v)
    await db.commit()
    await db.refresh(turno)
    return turno


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_turno(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_coordinador),
):
    turno = await db.get(Turno, id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    inst = await db.get(Instalacion, turno.instalacion_id)
    _assert_instalacion_pertenece(inst, current_user.empresa_id)
    turno.estado = EstadoTurno.cancelado
    await db.commit()
