#!/usr/bin/env python
"""
Test WhatsApp notification after configuration changes.
Run this after updating .env to verify credentials work.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings
from app.modules.adapters.notification import whatsapp_client


def main():
    print("=" * 60)
    print("WhatsApp Configuration Test")
    print("=" * 60)
    print()
    
    print("Current Configuration:")
    print(f"  Phone Number ID: {settings.whatsapp_phone_number_id}")
    print(f"  Admin Phone: {settings.whatsapp_admin_phone}")
    print(f"  Graph Version: {settings.whatsapp_graph_version}")
    print(f"  Access Token: {settings.whatsapp_access_token[:30]}...")
    print()
    
    if not settings.whatsapp_access_token:
        print("❌ WHATSAPP_ACCESS_TOKEN is not set!")
        return 1
    
    if not settings.whatsapp_phone_number_id:
        print("❌ WHATSAPP_PHONE_NUMBER_ID is not set!")
        return 1
    
    if not settings.whatsapp_admin_phone:
        print("❌ WHATSAPP_ADMIN_PHONE is not set!")
        return 1
    
    print("Sending test message...")
    try:
        result = whatsapp_client.send_message(
            settings.whatsapp_admin_phone,
            "✅ Test notifikasi dari IG Automation - WhatsApp berhasil dikonfigurasi!"
        )
        print()
        print("=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"Message sent successfully!")
        print(f"Response: {result}")
        return 0
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ FAILED!")
        print("=" * 60)
        print(f"Error: {type(e).__name__}: {e}")
        print()
        print("Possible issues:")
        print("  1. Access token expired or invalid")
        print("  2. Phone Number ID doesn't exist or no permission")
        print("  3. Phone number not registered for WhatsApp")
        print("  4. Network/firewall blocking Meta APIs")
        return 1


if __name__ == "__main__":
    sys.exit(main())
