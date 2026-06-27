import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum, ForeignKey,
    Integer, String, Text, Time, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── ENUMs (mirror SQL exactly) ─────────────────────────────────────────────

class RolEmpleado(str, enum.Enum):
    coordinador = "coordinador"
    trabajador = "trabajador"
    admin = "admin"


class TipoContrato(str, enum.Enum):
    tiempo_completo = "tiempo_completo"
    tiempo_parcial = "tiempo_parcial"
    eventual = "eventual"


class TipoRestriccion(str, enum.Enum):
    vacaciones = "vacaciones"
    baja_medica = "baja_medica"
    dia_libre_pactado = "dia_libre_pactado"
    no_disponible = "no_disponible"


class EstadoTurno(str, enum.Enum):
    programado = "programado"
    confirmado = "confirmado"
    cubierto = "cubierto"
    descubierto = "descubierto"
    completado = "completado"
    cancelado = "cancelado"


class EstadoSustitucion(str, enum.Enum):
    pendiente = "pendiente"
    aceptada = "aceptada"
    rechazada = "rechazada"
    expirada = "expirada"


# ── Models ─────────────────────────────────────────────────────────────────

class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cif: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="basico")
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    instalaciones: Mapped[List["Instalacion"]] = relationship(back_populates="empresa")
    empleados: Mapped[List["Empleado"]] = relationship(back_populates="empresa")


class Instalacion(Base):
    __tablename__ = "instalaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String(300))
    zonas_config: Mapped[Optional[str]] = mapped_column(Text)  # JSON string

    empresa: Mapped["Empresa"] = relationship(back_populates="instalaciones")
    turnos: Mapped[List["Turno"]] = relationship(back_populates="instalacion")


class Empleado(Base):
    __tablename__ = "empleados"
    __table_args__ = (
        CheckConstraint("horas_semana_max >= 1 AND horas_semana_max <= 48", name="empleados_horas_semana_max_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[RolEmpleado] = mapped_column(
        Enum(RolEmpleado, name="rol_empleado", create_type=False),
        nullable=False,
        default=RolEmpleado.trabajador,
    )
    tipo_contrato: Mapped[TipoContrato] = mapped_column(
        Enum(TipoContrato, name="tipo_contrato", create_type=False),
        nullable=False,
    )
    horas_semana_max: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    titulaciones: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(500))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="empleados")
    turnos: Mapped[List["Turno"]] = relationship(back_populates="empleado", foreign_keys="Turno.empleado_id")
    turnos_creados: Mapped[List["Turno"]] = relationship(back_populates="creado_por", foreign_keys="Turno.creado_por_id")
    restricciones: Mapped[List["Restriccion"]] = relationship(back_populates="empleado")
    cambios_solicitados: Mapped[List["CambioTurno"]] = relationship(back_populates="solicitante", foreign_keys="CambioTurno.solicitante_id")
    cambios_recibidos: Mapped[List["CambioTurno"]] = relationship(back_populates="receptor", foreign_keys="CambioTurno.receptor_id")


class Turno(Base):
    __tablename__ = "turnos"
    __table_args__ = (
        CheckConstraint("hora_fin > hora_inicio", name="turno_horario_valido"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instalacion_id: Mapped[int] = mapped_column(ForeignKey("instalaciones.id", ondelete="CASCADE"), nullable=False)
    empleado_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id", ondelete="SET NULL"))
    zona: Mapped[Optional[str]] = mapped_column(String(100))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hora_inicio: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    estado: Mapped[EstadoTurno] = mapped_column(
        Enum(EstadoTurno, name="estado_turno", create_type=False),
        nullable=False,
        default=EstadoTurno.programado,
    )
    notas: Mapped[Optional[str]] = mapped_column(Text)
    creado_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    actualizado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    instalacion: Mapped["Instalacion"] = relationship(back_populates="turnos")
    empleado: Mapped[Optional["Empleado"]] = relationship(back_populates="turnos", foreign_keys=[empleado_id])
    creado_por: Mapped[Optional["Empleado"]] = relationship(back_populates="turnos_creados", foreign_keys=[creado_por_id])
    cambios: Mapped[List["CambioTurno"]] = relationship(back_populates="turno")


class Restriccion(Base):
    __tablename__ = "restricciones"
    __table_args__ = (
        CheckConstraint("fecha_fin > fecha_inicio", name="restriccion_fechas_validas"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[TipoRestriccion] = mapped_column(
        Enum(TipoRestriccion, name="tipo_restriccion", create_type=False),
        nullable=False,
    )
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(String(300))
    aprobada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    empleado: Mapped["Empleado"] = relationship(back_populates="restricciones")


class CambioTurno(Base):
    """Historial inmutable — NUNCA se borra ni modifica una fila."""
    __tablename__ = "cambios_turno"
    __table_args__ = (
        CheckConstraint(
            "(estado = 'pendiente' AND resuelto_en IS NULL) OR (estado <> 'pendiente' AND resuelto_en IS NOT NULL)",
            name="cambio_resolucion_coherente",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    turno_id: Mapped[int] = mapped_column(ForeignKey("turnos.id", ondelete="CASCADE"), nullable=False)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("empleados.id", ondelete="CASCADE"), nullable=False)
    receptor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id", ondelete="SET NULL"))
    estado: Mapped[EstadoSustitucion] = mapped_column(
        Enum(EstadoSustitucion, name="estado_sustitucion", create_type=False),
        nullable=False,
        default=EstadoSustitucion.pendiente,
    )
    motivo_baja: Mapped[Optional[str]] = mapped_column(String(300))
    notas_coordinador: Mapped[Optional[str]] = mapped_column(Text)
    propuesto_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    resuelto_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    turno: Mapped["Turno"] = relationship(back_populates="cambios")
    solicitante: Mapped["Empleado"] = relationship(back_populates="cambios_solicitados", foreign_keys=[solicitante_id])
    receptor: Mapped[Optional["Empleado"]] = relationship(back_populates="cambios_recibidos", foreign_keys=[receptor_id])
