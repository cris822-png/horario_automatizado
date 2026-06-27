import pytest
from datetime import datetime

from httpx import AsyncClient


FECHA = "2025-07-14T00:00:00"


async def _create_instalacion(client, token):
    resp = await client.post(
        "/api/v1/instalaciones/",
        json={"nombre": "Piscina Central"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_turno_sin_empleado_descubierto(client: AsyncClient, coordinador_token, coordinador):
    inst_id = await _create_instalacion(client, coordinador_token)
    resp = await client.post(
        "/api/v1/turnos/",
        json={"instalacion_id": inst_id, "fecha": FECHA, "hora_inicio": "08:00", "hora_fin": "14:00"},
        headers={"Authorization": f"Bearer {coordinador_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["estado"] == "descubierto"


@pytest.mark.asyncio
async def test_turno_con_empleado_programado(client: AsyncClient, coordinador_token, trabajador):
    inst_id = await _create_instalacion(client, coordinador_token)
    resp = await client.post(
        "/api/v1/turnos/",
        json={
            "instalacion_id": inst_id,
            "empleado_id": trabajador.id,
            "fecha": FECHA,
            "hora_inicio": "08:00",
            "hora_fin": "10:00",
        },
        headers={"Authorization": f"Bearer {coordinador_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["estado"] == "programado"


@pytest.mark.asyncio
async def test_resumen_mes_estructura(client: AsyncClient, coordinador_token):
    inst_id = await _create_instalacion(client, coordinador_token)
    resp = await client.get(
        f"/api/v1/turnos/resumen?instalacion_id={inst_id}&mes=7&anio=2025",
        headers={"Authorization": f"Bearer {coordinador_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "descubiertos" in data
    assert "horas_por_empleado" in data
