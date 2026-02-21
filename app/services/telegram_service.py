"""
Telegram Bot API service for the chat interface.
Uses HTTPS requests to api.telegram.org; no heavy SDK required.
"""

import httpx
from typing import Dict, Any, Optional, List, Tuple
from app.utils.logger import get_logger
from app.utils.config import settings

logger = get_logger("telegram_service")


class TelegramService:
    """Telegram Bot API service: send messages, send photos, download media."""

    def __init__(self):
        self.token = (getattr(settings, "telegram_bot_token", None) or "").strip()
        self._base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured; Telegram chat interface disabled")

    def _enabled(self) -> bool:
        return bool(self._base_url)

    async def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Send a text message to a chat. chat_id is the Telegram chat id (e.g. from message.chat.id)."""
        if not self._enabled():
            return {"ok": False, "error": "Telegram bot token not configured"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{self._base_url}/sendMessage",
                    json={"chat_id": chat_id, "text": text[:4096]},
                )
                data = r.json()
                if not data.get("ok"):
                    logger.error(f"Telegram sendMessage failed: {data}")
                return data
        except Exception as e:
            logger.error(f"Telegram send_message error: {e}")
            return {"ok": False, "error": str(e)}

    async def send_photo(
        self, chat_id: str, image_bytes: bytes, caption: str = ""
    ) -> Dict[str, Any]:
        """Send a photo to a chat. image_bytes is the raw image data."""
        if not self._enabled():
            return {"ok": False, "error": "Telegram bot token not configured"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"chat_id": chat_id}
                if caption:
                    payload["caption"] = caption[:1024]
                files = {"photo": ("receipt.png", image_bytes, "image/png")}
                r = await client.post(
                    f"{self._base_url}/sendPhoto",
                    data=payload,
                    files=files,
                )
                data = r.json()
                if not data.get("ok"):
                    logger.error(f"Telegram sendPhoto failed: {data}")
                return data
        except Exception as e:
            logger.error(f"Telegram send_photo error: {e}")
            return {"ok": False, "error": str(e)}

    async def get_file_path(self, file_id: str) -> Optional[str]:
        """Get file_path from getFile for a given file_id. Returns None on failure."""
        if not self._enabled():
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self._base_url}/getFile",
                    json={"file_id": file_id},
                )
                data = r.json()
                if data.get("ok") and "result" in data:
                    return data["result"].get("file_path")
                return None
        except Exception as e:
            logger.error(f"Telegram getFile error: {e}")
            return None

    async def download_media(self, file_id: str) -> Optional[bytes]:
        """Download file by file_id (e.g. from message.photo[-1].file_id). Returns bytes or None."""
        if not self._enabled():
            return None
        file_path = await self.get_file_path(file_id)
        if not file_path:
            return None
        try:
            url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.content
                return None
        except Exception as e:
            logger.error(f"Telegram download_media error: {e}")
            return None

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Return getWebhookInfo result. If result.url is set, getUpdates will not receive updates."""
        if not self._enabled():
            return {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self._base_url}/getWebhookInfo")
                data = r.json()
                return data.get("result", {}) if data.get("ok") else {}
        except Exception as e:
            logger.debug(f"Telegram getWebhookInfo error: {e}")
            return {}

    async def delete_webhook(self) -> bool:
        """Remove webhook so getUpdates (long polling) can receive updates. Returns True on success."""
        if not self._enabled():
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(f"{self._base_url}/deleteWebhook")
                data = r.json()
                ok = data.get("ok", False)
                if ok:
                    logger.info("Telegram webhook removed; long polling can receive updates.")
                return ok
        except Exception as e:
            logger.warning(f"Telegram deleteWebhook error: {e}")
            return False

    async def get_updates(
        self, offset: Optional[int] = None, timeout: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Long polling: get updates from Telegram. Returns (list of updates, next_offset).
        Use next_offset for the next get_updates call so updates are not repeated.
        """
        if not self._enabled():
            return [], offset or 0
        try:
            params: Dict[str, Any] = {"timeout": timeout}
            if offset is not None:
                params["offset"] = offset
            async with httpx.AsyncClient(timeout=timeout + 5) as client:
                r = await client.get(f"{self._base_url}/getUpdates", params=params)
                data = r.json()
                if not data.get("ok"):
                    logger.warning(f"Telegram getUpdates failed: {data}")
                    return [], offset or 0
                results = data.get("result") or []
                next_offset = offset or 0
                if results:
                    next_offset = max(u.get("update_id", 0) for u in results) + 1
                return results, next_offset
        except Exception as e:
            logger.debug(f"Telegram get_updates error: {e}")
            return [], offset or 0


telegram_service = TelegramService()
