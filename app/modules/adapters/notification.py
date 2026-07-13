import logging
from datetime import UTC, datetime

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)


class TelegramClient:
    def send_message(self, recipient: str, message: str) -> dict[str, object]:
        if not settings.telegram_bot_token:
            return {"ok": True, "mock": True, "recipient": recipient, "message": message}

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        response = httpx.post(
            url,
            json={"chat_id": recipient, "text": message},
            timeout=20,
        )
        response.raise_for_status()
        return dict(response.json())


class WhatsAppClient:
    """
    WhatsApp client menggunakan Baileys service (WhatsApp Web API).
    Komunikasi via HTTP ke microservice Node.js.
    """
    
    def __init__(self):
        self.service_url = settings.whatsapp_service_url or "http://localhost:3001"
    
    def is_connected(self) -> bool:
        """Check apakah WhatsApp service terkoneksi."""
        try:
            response = httpx.get(f"{self.service_url}/health", timeout=5)
            data = response.json()
            return data.get("connected", False)
        except Exception as e:
            logger.error(f"Failed to check WhatsApp connection: {e}")
            return False
    
    def get_qr_code(self) -> str | None:
        """Dapatkan QR code untuk pairing (jika belum connected)."""
        try:
            response = httpx.get(f"{self.service_url}/qr", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("qr")
            return None
        except Exception as e:
            logger.error(f"Failed to get QR code: {e}")
            return None
    
    def list_groups(self) -> list[dict[str, object]]:
        """Dapatkan list group WhatsApp yang terhubung."""
        try:
            response = httpx.get(f"{self.service_url}/groups", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("groups", [])
            return []
        except Exception as e:
            logger.error(f"Failed to list groups: {e}")
            return []
    
    def send_message(self, recipient: str, message: str) -> dict[str, object]:
        """
        Kirim pesan WhatsApp via Baileys service.
        
        Args:
            recipient: Nomor WhatsApp atau Group ID
                      - Private: 628979755323 atau +628979755323
                      - Group: 120363XXXXX@g.us (langsung dari WhatsApp)
            message: Teks pesan
        
        Returns:
            Dict dengan status dan messageId jika berhasil
        
        Raises:
            RuntimeError: Jika service tidak terkoneksi atau gagal mengirim
        """
        if not recipient:
            raise RuntimeError("Recipient phone number atau group ID tidak boleh kosong")
        
        # Detect if group or private
        is_group = "@g.us" in recipient or "@c.us" in recipient
        
        if is_group:
            # Group ID sudah dalam format yang benar (e.g., 120363XXXXX@g.us)
            normalized_recipient = recipient
        else:
            # Private chat - normalize phone number
            normalized_recipient = normalize_whatsapp_phone_number(recipient)
        
        recipient_type = "group" if is_group else "private"
        logger.info(f"Sending WhatsApp message to {recipient_type}: {normalized_recipient} via Baileys")
        
        try:
            response = httpx.post(
                f"{self.service_url}/send",
                json={
                    "to": normalized_recipient,
                    "message": message
                },
                timeout=20,
            )
            
            if response.status_code == 503:
                raise RuntimeError(
                    "WhatsApp Baileys service tidak terkoneksi. "
                    "Scan QR code terlebih dahulu via /admin/whatsapp/qr"
                )
            
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", "Unknown error")
                logger.error(f"Baileys service error: {response.status_code} - {error_msg}")
                raise RuntimeError(f"Failed to send WhatsApp message: {error_msg}")
            
            result = response.json()
            logger.info(f"WhatsApp message sent successfully to {recipient_type}: {result.get('messageId')}")
            return result
            
        except httpx.ConnectError:
            raise RuntimeError(
                "Tidak bisa terhubung ke WhatsApp Baileys service. "
                "Pastikan service berjalan di docker-compose."
            )
        except httpx.TimeoutException:
            raise RuntimeError("WhatsApp service timeout. Service mungkin sibuk.")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            logger.error(f"Unexpected error sending WhatsApp: {e}")
            raise RuntimeError(f"Failed to send WhatsApp message: {str(e)}")


def normalize_whatsapp_phone_number(value: str) -> str:
    cleaned = (
        value.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    if not cleaned.isdigit():
        raise RuntimeError(
            "WHATSAPP_ADMIN_PHONE hanya boleh berisi digit, spasi, '-', '()', atau prefix '+'."
        )
    if cleaned.startswith("0"):
        return f"62{cleaned[1:]}"
    if cleaned.startswith("8"):
        return f"62{cleaned}"
    return cleaned


def build_review_message(
    article_id: int,
    title: str,
    timestamp: datetime | None = None,
    instagram_username: str | None = None,
    category: str | None = None,
) -> str:
    """
    Build pesan notifikasi dengan gaya redaksi berita yang menarik.
    
    Args:
        article_id: ID artikel draft
        title: Judul artikel (kalimat pertama)
        timestamp: Waktu posting (opsional, dalam UTC)
        instagram_username: Username Instagram author (opsional)
        category: Kategori artikel (opsional)
    """
    # Format timestamp dengan timezone WIB (UTC+7)
    if timestamp:
        # Convert UTC to WIB (UTC+7)
        from datetime import timedelta
        wib_time = timestamp + timedelta(hours=7)
        time_str = wib_time.strftime("%d %B %Y, %H:%M WIB")
    else:
        from datetime import timedelta
        wib_time = datetime.now(UTC) + timedelta(hours=7)
        time_str = wib_time.strftime("%d %B %Y, %H:%M WIB")
    
    # Build author line
    author_line = f"👤 @{instagram_username}" if instagram_username else "👤 Tim Redaksi"
    
    # Build category badge
    category_badge = f"📁 {category}" if category else "📁 Artikel Baru"
    
    # Emojis untuk menarik perhatian
    emojis = ["✨", "🎯", "🚀", "💡", "🔥", "⭐"]
    emoji = emojis[article_id % len(emojis)]  # Variasi emoji berdasarkan ID
    
    return (
        f"{emoji} *ARTIKEL BARU SIAP TAYANG!* {emoji}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📰 *{title}*\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {time_str}\n"
        f"{author_line}\n"
        f"{category_badge}\n"
        f"\n"
        f"🎬 *Konten fresh dari Instagram sudah kami olah jadi artikel menarik!*\n"
        f"\n"
        f"Yuk, cek dulu sebelum dipublikasikan:\n"
        f"👉 {settings.public_base_url}/admin/articles/drafts/{article_id}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *AKSI CEPAT:*\n"
        f"✅ Approve → Publish\n"
        f"✏️ Edit → Revisi konten\n"
        f"❌ Reject → Buang draft\n"
        f"\n"
        f"_Konten berkualitas dimulai dari review yang teliti!_ 🎯"
    )


telegram_client = TelegramClient()
whatsapp_client = WhatsAppClient()


def utcnow() -> datetime:
    return datetime.now(UTC)
