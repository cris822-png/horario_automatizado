from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator

from app.models.models import (
    RolEmpleado, TipoContrato, TipoRestriccion,
    EstadoTurno, EstadoSustitucion,
)


# ── Token ──────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: int
    rol: RolEmpleado
    empresa_id: int


# ── Empresa ────────────────────────────────────────────────────────────────

class EmpresaOut(BaseModel):
    id: int
    nombre: str
    cif: Optional[str] = None
    plan: str
    activa: bool
    creada_en: datetime

    model_config = {"from_attributes": True}


# ── Instalacion ────────────────────────────────────────────────────────────

class InstalacionCreate(BaseModel):
    nombre: str
    direccion: Optional[str] = None
    zonas_config: Optional[str] = None  # JSON string


class InstalacionUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    zonas_config: Optional[str] = None


class InstalacionOut(BaseModel):
    id: int
    empresa_id: int
    nombre: str
    direccion: Optional[str] = None
    zonas_config: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Empleado ───────────────────────────────────────────────────────────────

class EmpleadoCreate(BaseModel):
    nombre: str
    apellidos: str
    email: EmailStr
    telefono: Optional[str] = None
    password: str
    rol: RolEmpleado = RolEmpleado.trabajador
    tipo_contrato: TipoContrato
    horas_semana_max: int = 40
    titulaciones: List[str] = []

    @field_validator("horas_semana_max")
    @classmethod
    def horas_validas(cls, v: int) -> int:
        if not (1 <= v <= 48):
            raise ValueError("horas_semana_max debe estar entre 1 y 48")
        return v


class EmpleadoUpdate(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    telefono: Optional[str] = None
    rol: Optional[RolEmpleado] = None
    tipo_contrato: Optional[TipoContrato] = None
    horas_semana_max: Optional[int] = None
    titulaciones: Optional[List[str]] = None
    activo: Optional[bool] = None
    fcm_token: Optional[str] = None

    @field_validator("horas_semana_max")
    @classmethod
    def horas_validas(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 48):
            raise ValueError("horas_semana_max debe estar entre 1 y 48")
        return v


class EmpleadoOut(BaseModel):
    id: int
    empresa_id: int
    nombre: str
    apellidos: str
    email: str
    telefono: Optional[str] = None
    rol: RolEmpleado
    tipo_contrato: TipoContrato
    horas_semana_max: int
    titulaciones: List[str]
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


# ── Turno ──────────────────────────────────────────────────────────────────

class TurnoCreate(BaseModel):
    instalacion_id: int
    empleado_id: Optional[int] = None
    zona: Optional[str] = None
    fecha: datetime
    hora_inicio: str  # "HH:MM"
    hora_fin: str     # "HH:MM"
    notas: Optional[str] = None

    @field_validator("hora_fin")
    @classmethod
    def fin_despues_inicio(cls, v: str, info) -> str:
        inicio = info.data.get("hora_inicio")
        if inicio and v <= inicio:
            raise ValueError("hora_fin debe ser posterior a hora_inicio")
        return v


class TurnoUpdate(BaseModel):
    empleado_id: Optional[int] = None
    zona: Optional[str] = None
    fecha: Optional[datetime] = None
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    estado: Optional[EstadoTurno] = None
    notas: Optional[str] = None


class EmpleadoResumen(BaseModel):
    id: int
    nombre: str
    apellidos: str

    model_config = {"from_attributes": True}


class TurnoOut(BaseModel):
    id: int
    instalacion_id: int
    empleado_id: Optional[int] = None
    zona: Optional[str] = None
    fecha: datetime
    hora_inicio: str
    hora_fin: str
    estado: EstadoTurno
    notas: Optional[str] = None
    creado_en: datetime
    actualizado_en: Optional[datetime] = None
    empleado: Optional[EmpleadoResumen] = None

    model_config = {"from_attributes": True}


class ResumenCuadro(BaseModel):
    total: int
    descubiertos: int
    programados: int
    confirmados: int
    completados: int
    cancelados: int
    horas_por_empleado: dict


# ── Restriccion ────────────────────────────────────────────────────────────

class RestriccionCreate(BaseModel):
    empleado_id: int
    tipo: TipoRestriccion
    fecha_inicio: datetime
    fecha_fin: datetime
    motivo: Optional[str] = None

    @field_validator("fecha_fin")
    @classmethod
    def fin_despues_inicio(cls, v: datetime, info) -> datetime:
        inicio = info.data.get("fecha_inicio")
        if inicio and v <= inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return v


class RestriccionUpdate(BaseModel):
    tipo: Optional[TipoRestriccion] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    motivo: Optional[str] = None
    aprobada: Optional[bool] = None


class RestriccionOut(BaseModel):
    id: int
    empleado_id: int
    tipo: TipoRestriccion
    fecha_inicio: datetime
    fecha_fin: datetime
    motivo: Optional[str] = None
    aprobada: bool
    creada_en: datetime

    model_config = {"from_attributes": True}


# ── CambioTurno / Sustitucion ──────────────────────────────────────────────

class CambioTurnoOut(BaseModel):
    id: int
    turno_id: int
    solicitante_id: int
    receptor_id: Optional[int] = None
    estado: EstadoSustitucion
    motivo_baja: Optional[str] = None
    notas_coordinador: Optional[str] = None
    propuesto_en: datetime
    resuelto_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportarBajaIn(BaseModel):
    turno_id: int
    motivo_baja: Optional[str] = None


class ProponerSustitutoIn(BaseModel):
    receptor_id: int


class ResponderSustitucionIn(BaseModel):
    acepta: bool


# ── Validacion ─────────────────────────────────────────────────────────────

class ValidacionTurno(BaseModel):
    valido: bool
    advertencias: List[str] = []
    errores: List[str] = []


class CandidatoSustitucion(BaseModel):
    empleado: EmpleadoOut
    horas_semana_actual: float
    horas_disponibles: float
    cumple_titulacion: bool
    score: int
