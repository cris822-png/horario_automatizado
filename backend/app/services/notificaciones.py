"""
Servicio de notificaciones.
Canal primario: FCM (Firebase Cloud Messaging v1 HTTP API).
Canal fallback: WhatsApp Business Cloud API (Meta).
Todos los métodos son async, capturan excepciones y loguean sin propagar.
"""
import logging
import httpx

from app.core.config import settings
from app.models.models import Empleado

logger = logging.getLogger(__name__)


class NotificacionService:
    async def notificar_turno_asignado(self, empleado: Empleado, turno_id: int) -> None:
        await self._enviar(
            empleado,
            titulo="Turno asignado",
            cuerpo=f"Se te ha asignado el turno #{turno_id}. Revisa tu calendario.",
        )

    async def notificar_solicitud_sustitucion(self, empleado: Empleado, turno_id: int) -> None:
        await self._enviar(
            empleado,
            titulo="Solicitud de sustitución",
            cuerpo=f"Se te propone cubrir el turno #{turno_id}. Acepta o rechaza en la app.",
        )

    async def notificar_turno_confirmado(self, empleado: Empleado, turno_id: int) -> None:
        await self._enviar(
            empleado,
            titulo="Turno confirmado",
            cuerpo=f"Tu turno #{turno_id} ha sido confirmado.",
        )

    async def notificar_baja_cubierta(self, coordinador: Empleado, turno_id: int) -> None:
        await self._enviar(
            coordinador,
            titulo="Baja cubierta",
            cuerpo=f"El turno #{turno_id} ha sido cubierto exitosamente.",
        )

    async def _enviar(self, empleado: Empleado, titulo: str, cuerpo: str) -> None:
        if empleado.fcm_token and settings.FCM_SERVER_KEY:
            await self._fcm(empleado.fcm_token, titulo, cuerpo)
        elif empleado.telefono and settings.WHATSAPP_API_TOKEN:
            await self._whatsapp(empleado.telefono, f"{titulo}: {cuerpo}")
        else:
            logger.debug("Sin canal de notificación para empleado %s", empleado.id)

    async def _fcm(self, token: str, titulo: str, cuerpo: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://fcm.googleapis.com/fcm/send",
                    headers={"Authorization": f"key={settings.FCM_SERVER_KEY}"},
                    json={
                        "to": token,
                        "notification": {"title": titulo, "body": cuerpo},
                    },
                )
                resp.raise_for_status()
        except Exception as exc:
            logger.error("FCM error para token %s: %s", token[:20], exc)

    async def _whatsapp(self, telefono: str, mensaje: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages",
                    headers={"Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}"},
                    json={
                        "messaging_product": "whatsapp",
                        "to": telefono,
                        "type": "text",
                        "text": {"body": mensaje},
                    },
                )
                resp.raise_for_status()
        except Exception as exc:
            logger.error("WhatsApp error para %s: %s", telefono, exc)


notificacion_service = NotificacionService()
