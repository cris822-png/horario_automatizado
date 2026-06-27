"""
Fixtures async para tests. Usa SQLite en memoria (aiosqlite) para aislamiento.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.base import Base
from app.models.models import Empresa, Empleado, RolEmpleado, TipoContrato
from app.core.security import get_password_hash, create_access_token

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    # SQLite: ENUMs no existen, los modelos usan String internamente en tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def empresa(db_session):
    e = Empresa(nombre="Empresa Test", plan="profesional")
    db_session.add(e)
    await db_session.commit()
    await db_session.refresh(e)
    return e


@pytest_asyncio.fixture
async def coordinador(db_session, empresa):
    emp = Empleado(
        empresa_id=empresa.id,
        nombre="Ana",
        apellidos="García",
        email="ana@test.com",
        password_hash=get_password_hash("secret"),
        rol=RolEmpleado.coordinador,
        tipo_contrato=TipoContrato.tiempo_completo,
        horas_semana_max=40,
        titulaciones=[],
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)
    return emp


@pytest_asyncio.fixture
async def trabajador(db_session, empresa):
    emp = Empleado(
        empresa_id=empresa.id,
        nombre="Luis",
        apellidos="Pérez",
        email="luis@test.com",
        password_hash=get_password_hash("secret"),
        rol=RolEmpleado.trabajador,
        tipo_contrato=TipoContrato.tiempo_parcial,
        horas_semana_max=20,
        titulaciones=["socorrista"],
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)
    return emp


@pytest_asyncio.fixture
def coordinador_token(coordinador, empresa):
    return create_access_token({"sub": str(coordinador.id), "rol": coordinador.rol.value, "empresa_id": empresa.id})


@pytest_asyncio.fixture
def trabajador_token(trabajador, empresa):
    return create_access_token({"sub": str(trabajador.id), "rol": trabajador.rol.value, "empresa_id": empresa.id})
