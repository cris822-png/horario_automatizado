"""
Motor de restricciones y sustituciones.

MotorValidacion: valida si un turno puede asignarse a un empleado.
MotorSustituciones: puntúa candidatos para cubrir un turno descubierto.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Empleado, Turno, Restriccion, EstadoTurno
from app.schemas.schemas import ValidacionTurno, CandidatoSustitucion


class MotorValidacion:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validar(
        self,
        empleado_id: int,
        instalacion_id: int,
        fecha: datetime,
        hora_inicio: str,
        hora_fin: str,
        zona: str | None = None,
        excluir_turno_id: int | None = None,
    ) -> ValidacionTurno:
        errores: List[str] = []
        advertencias: List[str] = []

        # 1. Empleado activo
        emp = await self.db.get(Empleado, empleado_id)
        if not emp or not emp.activo:
            return ValidacionTurno(valido=False, errores=["Empleado inactivo o no encontrado"])

        # 2. Restricción activa solapada
        inicio_dt = datetime.combine(fecha.date(), _parse_time(hora_inicio))
        fin_dt = datetime.combine(fecha.date(), _parse_time(hora_fin))

        q = select(Restriccion).where(
            Restriccion.empleado_id == empleado_id,
            Restriccion.aprobada == True,
            Restriccion.fecha_inicio <= fin_dt,
            Restriccion.fecha_fin >= inicio_dt,
        )
        result = await self.db.execute(q)
        if result.scalar_one_or_none():
            errores.append("El empleado tiene una restricción activa que solapa con este turno")

        # 3 & 4. Horas semanales
        semana_inicio = fecha - timedelta(days=fecha.weekday())
        semana_fin = semana_inicio + timedelta(days=7)

        q_horas = select(Turno).where(
            Turno.empleado_id == empleado_id,
            Turno.fecha >= semana_inicio,
            Turno.fecha < semana_fin,
            Turno.estado.not_in([EstadoTurno.cancelado]),
        )
        if excluir_turno_id:
            q_horas = q_horas.where(Turno.id != excluir_turno_id)
        turnos_semana = (await self.db.execute(q_horas)).scalars().all()

        horas_actuales = sum(
            _duracion_horas(t.hora_inicio, t.hora_fin) for t in turnos_semana
        )
        duracion_nuevo = _duracion_horas(_parse_time(hora_inicio), _parse_time(hora_fin))
        horas_tras_asignar = horas_actuales + duracion_nuevo

        if horas_tras_asignar > emp.horas_semana_max:
            errores.append(
                f"Supera el máximo semanal: {horas_tras_asignar:.1f}h > {emp.horas_semana_max}h"
            )
        elif horas_tras_asignar > emp.horas_semana_max * 0.9:
            advertencias.append(
                f"Al 90% del máximo semanal ({horas_tras_asignar:.1f}/{emp.horas_semana_max}h)"
            )

        # 5. Descanso mínimo entre turnos consecutivos
        min_descanso = timedelta(hours=settings.DESCANSO_MIN_ENTRE_TURNOS_HORAS)
        q_prev = select(Turno).where(
            Turno.empleado_id == empleado_id,
            Turno.estado.not_in([EstadoTurno.cancelado]),
            Turno.fecha >= fecha - timedelta(days=2),
            Turno.fecha <= fecha + timedelta(days=2),
        )
        if excluir_turno_id:
            q_prev = q_prev.where(Turno.id != excluir_turno_id)
        turnos_cercanos = (await self.db.execute(q_prev)).scalars().all()

        for t in turnos_cercanos:
            t_inicio = datetime.combine(t.fecha.date(), t.hora_inicio)
            t_fin = datetime.combine(t.fecha.date(), t.hora_fin)
            gap_antes = inicio_dt - t_fin
            gap_despues = t_inicio - fin_dt
            if timedelta(0) <= gap_antes < min_descanso:
                errores.append(
                    f"Descanso insuficiente: solo {gap_antes.seconds // 3600}h antes del turno #{t.id}"
                )
            if timedelta(0) <= gap_despues < min_descanso:
                errores.append(
                    f"Descanso insuficiente: solo {gap_despues.seconds // 3600}h después del turno #{t.id}"
                )

        # 6. Titulación requerida por zona
        if zona:
            from app.models.models import Instalacion
            inst = await self.db.get(Instalacion, instalacion_id)
            if inst and inst.zonas_config:
                try:
                    zonas = json.loads(inst.zonas_config)
                    zona_cfg = next((z for z in zonas if z.get("nombre") == zona), None)
                    if zona_cfg:
                        titulacion_req = zona_cfg.get("titulacion_requerida")
                        if titulacion_req and titulacion_req not in (emp.titulaciones or []):
                            errores.append(
                                f"El empleado no tiene la titulación requerida para la zona '{zona}': {titulacion_req}"
                            )
                except (json.JSONDecodeError, KeyError):
                    pass  # ponytail: zonas_config malformado, ignorar silenciosamente

        return ValidacionTurno(
            valido=len(errores) == 0,
            advertencias=advertencias,
            errores=errores,
        )


class MotorSustituciones:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def puntuar_candidatos(
        self, turno: Turno, candidatos: List[Empleado]
    ) -> List[CandidatoSustitucion]:
        motor = MotorValidacion(self.db)
        result = []
        for emp in candidatos:
            hora_inicio = turno.hora_inicio.strftime("%H:%M")
            hora_fin = turno.hora_fin.strftime("%H:%M")

            validacion = await motor.validar(
                empleado_id=emp.id,
                instalacion_id=turno.instalacion_id,
                fecha=turno.fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                zona=turno.zona,
                excluir_turno_id=turno.id,
            )

            # horas actuales esta semana
            semana_inicio = turno.fecha - timedelta(days=turno.fecha.weekday())
            semana_fin = semana_inicio + timedelta(days=7)
            q = select(Turno).where(
                Turno.empleado_id == emp.id,
                Turno.fecha >= semana_inicio,
                Turno.fecha < semana_fin,
                Turno.estado.not_in([EstadoTurno.cancelado]),
            )
            turnos_sem = (await self.db.execute(q)).scalars().all()
            horas_actuales = sum(_duracion_horas(t.hora_inicio, t.hora_fin) for t in turnos_sem)
            horas_disponibles = max(0.0, emp.horas_semana_max - horas_actuales)

            # Scoring 0–100
            score = 0

            # Titulación: +40
            cumple_titulacion = True
            if turno.zona:
                from app.models.models import Instalacion
                inst = await self.db.get(Instalacion, turno.instalacion_id)
                if inst and inst.zonas_config:
                    try:
                        zonas = json.loads(inst.zonas_config)
                        zona_cfg = next((z for z in zonas if z.get("nombre") == turno.zona), None)
                        if zona_cfg:
                            tit_req = zona_cfg.get("titulacion_requerida")
                            if tit_req:
                                cumple_titulacion = tit_req in (emp.titulaciones or [])
                    except (json.JSONDecodeError, KeyError):
                        pass
            if cumple_titulacion:
                score += 40

            # Margen horario: +30 proporcional
            if emp.horas_semana_max > 0:
                ratio = min(1.0, horas_disponibles / emp.horas_semana_max)
                score += int(ratio * 30)

            # Sin advertencias: +20
            if not validacion.advertencias and not validacion.errores:
                score += 20

            # Contrato tiempo completo: +10
            from app.models.models import TipoContrato
            if emp.tipo_contrato == TipoContrato.tiempo_completo:
                score += 10

            from app.schemas.schemas import EmpleadoOut
            result.append(CandidatoSustitucion(
                empleado=EmpleadoOut.model_validate(emp),
                horas_semana_actual=horas_actuales,
                horas_disponibles=horas_disponibles,
                cumple_titulacion=cumple_titulacion,
                score=min(100, score),
            ))

        result.sort(key=lambda c: c.score, reverse=True)
        return result


# ── helpers ────────────────────────────────────────────────────────────────

def _parse_time(t):
    """Accept a time object or 'HH:MM' string."""
    if hasattr(t, "hour"):
        return t
    from datetime import time as dtime
    h, m = map(int, t.split(":"))
    return dtime(h, m)


def _duracion_horas(inicio, fin) -> float:
    inicio = _parse_time(inicio)
    fin = _parse_time(fin)
    return (fin.hour * 60 + fin.minute - inicio.hour * 60 - inicio.minute) / 60
