from fastapi import APIRouter
from app.api.v1.endpoints import auth, empresas, instalaciones, empleados, turnos, restricciones, sustituciones

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(instalaciones.router)
router.include_router(empleados.router)
router.include_router(turnos.router)
router.include_router(restricciones.router)
router.include_router(sustituciones.router)
