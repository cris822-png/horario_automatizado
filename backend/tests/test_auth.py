import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_correcto(client: AsyncClient, coordinador):
    resp = await client.post("/api/v1/auth/login", data={"username": coordinador.email, "password": "secret"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_incorrecto(client: AsyncClient, coordinador):
    resp = await client.post("/api/v1/auth/login", data={"username": coordinador.email, "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_sin_token(client: AsyncClient):
    resp = await client.get("/api/v1/empleados/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_trabajador_accede_endpoint_coordinador(client: AsyncClient, trabajador_token):
    resp = await client.get(
        "/api/v1/empresas/me",
        headers={"Authorization": f"Bearer {trabajador_token}"},
    )
    assert resp.status_code == 403
