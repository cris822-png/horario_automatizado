"""Tests for MotorValidacion and MotorSustituciones."""
import pytest
from datetime import datetime, timedelta

from app.models.models import Empleado, RolEmpleado, TipoContrato, Restriccion, TipoRestriccion, Turno, EstadoTurno
from app.services.motor_restricciones import MotorValidacion, MotorSustituciones
from app.core.security import get_password_hash


def _mk_empleado(db_session, empresa_id, activo=True, horas_max=40, titulaciones=None):
    import uuid
    emp = Empleado(
        empresa_id=empresa_id,
        nombre="Test",
        apellidos="User",
        email=f"test_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=get_password_hash("x"),
        rol=RolEmpleado.trabajador,
        tipo_contrato=TipoContrato.tiempo_completo,
        horas_semana_max=horas_max,
        titulaciones=titulaciones or [],
        activo=activo,
    )
    db_session.add(emp)
    return emp


FECHA = datetime(2025, 7, 14, 9, 0)


@pytest.mark.asyncio
async def test_empleado_inactivo(db_session, empresa):
    emp = _mk_empleado(db_session, empresa.id, activo=False)
    await db_session.commit()
    await db_session.refresh(emp)
    motor = MotorValidacion(db_session)
    r = await motor.validar(emp.id, 1, FECHA, "08:00", "10:00")
    assert not r.valido
    assert any("inactivo" in e.lower() for e in r.errores)


@pytest.mark.asyncio
async def test_sin_restricciones_valido(db_session, empresa):
    emp = _mk_empleado(db_session, empresa.id)
    await db_session.commit()
    await db_session.refresh(emp)
    motor = MotorValidacion(db_session)
    r = await motor.validar(emp.id, 1, FECHA, "08:00", "10:00")
    assert r.valido


@pytest.mark.asyncio
async def test_superar_horas_convenio(db_session, empresa):
    emp = _mk_empleado(db_session, empresa.id, horas_max=8)
    await db_session.commit()
    await db_session.refresh(emp)
    motor = MotorValidacion(db_session)
    # 9 horas supera el max de 8
    r = await motor.validar(emp.id, 1, FECHA, "08:00", "17:00")
    assert not r.valido
    assert any("máximo semanal" in e.lower() for e in r.errores)


@pytest.mark.asyncio
async def test_al_90_porciento_advertencia(db_session, empresa):
    emp = _mk_empleado(db_session, empresa.id, horas_max=10)
    await db_session.commit()
    await db_session.refresh(emp)
    motor = MotorValidacion(db_session)
    # 9 horas = 90% de 10 → advertencia, no error
    r = await motor.validar(emp.id, 1, FECHA, "08:00", "17:00")
    assert r.valido
    assert r.advertencias


@pytest.mark.asyncio
async def test_restriccion_activa_bloquea(db_session, empresa):
    emp = _mk_empleado(db_session, empresa.id)
    await db_session.commit()
    await db_session.refresh(emp)
    restriccion = Restriccion(
        empleado_id=emp.id,
        tipo=TipoRestriccion.vacaciones,
        fecha_inicio=FECHA - timedelta(days=1),
        fecha_fin=FECHA + timedelta(days=1),
        aprobada=True,
    )
    db_session.add(restriccion)
    await db_session.commit()
    motor = MotorValidacion(db_session)
    r = await motor.validar(emp.id, 1, FECHA, "08:00", "10:00")
    assert not r.valido


@pytest.mark.asyncio
async def test_score_mayor_con_titulacion(db_session, empresa):
    """Score con titulación > score sin titulación cuando zona la requiere."""
    # Sin instalación con zona_config, scoring basado solo en horas y contrato
    emp_con = _mk_empleado(db_session, empresa.id, titulaciones=["socorrista"])
    emp_sin = _mk_empleado(db_session, empresa.id, titulaciones=[])
    await db_session.commit()
    await db_session.refresh(emp_con)
    await db_session.refresh(emp_sin)

    from app.models.models import Instalacion
    inst = Instalacion(empresa_id=empresa.id, nombre="Piscina", zonas_config='[{"nombre":"vaso","titulacion_requerida":"socorrista"}]')
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    turno = Turno(
        instalacion_id=inst.id,
        zona="vaso",
        fecha=FECHA,
        hora_inicio=__import__("datetime").time(8, 0),
        hora_fin=__import__("datetime").time(10, 0),
        estado=EstadoTurno.descubierto,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)

    motor = MotorSustituciones(db_session)
    resultados = await motor.puntuar_candidatos(turno, [emp_con, emp_sin])
    scores = {c.empleado.id: c.score for c in resultados}
    assert scores[emp_con.id] > scores[emp_sin.id]
