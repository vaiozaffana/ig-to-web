#!/usr/bin/env python
"""
Test WhatsApp Baileys service.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings
from app.modules.adapters.notification import whatsapp_client


def main():
    print("=" * 70)
    print("WhatsApp Baileys Service Test")
    print("=" * 70)
    print()
    
    print(f"Service URL: {settings.whatsapp_service_url}")
    print(f"Admin Phone: {settings.whatsapp_admin_phone}")
    print()
    
    # Check connection
    print("Checking WhatsApp connection...")
    is_connected = whatsapp_client.is_connected()
    
    if not is_connected:
        print("❌ WhatsApp belum terkoneksi!")
        print()
        print("Untuk connect:")
        print("  1. Pastikan service berjalan: docker compose ps whatsapp")
        print("  2. Dapatkan QR code: curl http://localhost:8000/admin/whatsapp/qr \\")
        print("       -H 'X-Admin-API-Key: your-key'")
        print("  3. Scan QR dengan WhatsApp: Settings → Linked Devices → Link a Device")
        print()
        
        # Try get QR
        qr = whatsapp_client.get_qr_code()
        if qr:
            print("QR Code tersedia! Scan dengan WhatsApp:")
            print()
            # Print QR as terminal (jika ada library qrcode)
            try:
                import qrcode
                qr_obj = qrcode.QRCode()
                qr_obj.add_data(qr)
                qr_obj.print_ascii()
            except ImportError:
                print(f"QR Data: {qr[:50]}...")
                print("(Install 'qrcode' library untuk display QR di terminal)")
        
        return 1
    
    print("✅ WhatsApp connected!")
    print()
    
    if not settings.whatsapp_admin_phone:
        print("⚠️  WHATSAPP_ADMIN_PHONE belum diset di .env")
        return 1
    
    # Send test message
    print(f"Sending test message to {settings.whatsapp_admin_phone}...")
    try:
        result = whatsapp_client.send_message(
            settings.whatsapp_admin_phone,
            "✅ Test dari IG Automation - WhatsApp Baileys berhasil!"
        )
        print()
        print("=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70)
        print(f"Message ID: {result.get('messageId')}")
        print(f"Sent to: {result.get('to')}")
        return 0
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ FAILED!")
        print("=" * 70)
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
