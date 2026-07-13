#!/usr/bin/env python
"""
List WhatsApp groups dan test kirim ke group.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings
from app.modules.adapters.notification import whatsapp_client


def main():
    print("=" * 70)
    print("WhatsApp Groups Management")
    print("=" * 70)
    print()
    
    # Check connection
    if not whatsapp_client.is_connected():
        print("❌ WhatsApp tidak terkoneksi!")
        print("Scan QR code terlebih dahulu: curl http://localhost:8000/admin/whatsapp/qr")
        return 1
    
    print("✅ WhatsApp connected")
    print()
    
    # List groups
    print("Fetching groups...")
    groups = whatsapp_client.list_groups()
    
    if not groups:
        print("ℹ️  No groups found")
        print()
        print("Tips:")
        print("  - Pastikan akun WhatsApp yang di-scan adalah member dari group")
        print("  - Refresh dengan restart WhatsApp service jika baru join group")
        return 0
    
    print(f"Found {len(groups)} groups:")
    print()
    
    for i, group in enumerate(groups, 1):
        print(f"{i}. {group['subject']}")
        print(f"   ID: {group['id']}")
        print(f"   Participants: {group['participants']}")
        print()
    
    # Show current config
    print("=" * 70)
    print("Current Configuration")
    print("=" * 70)
    print(f"Mode: {settings.whatsapp_notification_mode}")
    print(f"Group ID: {settings.whatsapp_group_id or '(not set)'}")
    print(f"Admin Phone: {settings.whatsapp_admin_phone or '(not set)'}")
    print()
    
    # Test send if group configured
    if settings.whatsapp_notification_mode == "group" and settings.whatsapp_group_id:
        print("=" * 70)
        print("Testing Group Notification")
        print("=" * 70)
        
        test_message = "🧪 Test notifikasi ke group - IG Automation"
        
        try:
            result = whatsapp_client.send_message(
                settings.whatsapp_group_id,
                test_message
            )
            print("✅ Message sent to group!")
            print(f"Message ID: {result.get('messageId')}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            return 1
    else:
        print("ℹ️  To test group notification:")
        print("  1. Set WHATSAPP_GROUP_ID=<group_id> in .env")
        print("  2. Set WHATSAPP_NOTIFICATION_MODE=group in .env")
        print("  3. Restart services: docker compose restart api worker beat")
        print("  4. Run this script again")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
