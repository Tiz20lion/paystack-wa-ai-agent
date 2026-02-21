"""
Telegram Bot API service for the chat interface.
Uses HTTPS requests to api.telegram.org; no heavy SDK required.
"""

import httpx
from typing import Dict, Any, Optional
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


telegram_service = TelegramService()
