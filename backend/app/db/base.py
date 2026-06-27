# Import all models here so Alembic autogenerate detects them
from app.db.session import engine  # noqa: F401
from app.models.models import Base, Empresa, Instalacion, Empleado, Turno, Restriccion, CambioTurno  # noqa: F401
