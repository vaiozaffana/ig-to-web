#!/usr/bin/env python
"""
Test notification fallback mechanism.
Tests both WhatsApp and Telegram notification paths.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings
from app.modules.agents.notification_agent import send_admin_message


def main():
    print("=" * 60)
    print("Notification Fallback Test")
    print("=" * 60)
    print()
    
    print("Configuration:")
    print(f"  WhatsApp Phone Number ID: {settings.whatsapp_phone_number_id}")
    print(f"  WhatsApp Admin Phone: {settings.whatsapp_admin_phone}")
    print(f"  Telegram Admin Chat ID: {settings.telegram_admin_chat_id}")
    print()
    
    message = "🧪 Test notifikasi - Fallback mechanism check"
    
    print("Sending test notification via send_admin_message()...")
    print("(Will try WhatsApp first, fallback to Telegram if fails)")
    print()
    
    try:
        result = send_admin_message(
            settings.whatsapp_admin_phone,
            message
        )
        print("=" * 60)
        print("✅ Notification Sent Successfully!")
        print("=" * 60)
        print(f"Result: {result}")
        print()
        
        if result.get("mock"):
            print("ℹ️  Note: This was a mock response (credentials not configured)")
        
        return 0
    except Exception as e:
        print("=" * 60)
        print("❌ Both WhatsApp and Telegram Failed!")
        print("=" * 60)
        print(f"Error: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
