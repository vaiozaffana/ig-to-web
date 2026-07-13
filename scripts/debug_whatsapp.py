#!/usr/bin/env python
"""
Debug WhatsApp Baileys connection dan konfigurasi.
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings


def main():
    print("=" * 70)
    print("WhatsApp Baileys Debug")
    print("=" * 70)
    print()
    
    # Check service health
    print("1. Checking WhatsApp service...")
    try:
        response = httpx.get(f"{settings.whatsapp_service_url}/health", timeout=5)
        health = response.json()
        
        print(f"   Status: {health.get('status')}")
        print(f"   Connected: {health.get('connected')}")
        
        if health.get('user'):
            user = health['user']
            user_id = user.get('id', 'unknown')
            user_name = user.get('name', 'No name')
            
            # Extract nomor dari user ID
            sender_number = user_id.split(':')[0] if ':' in user_id else user_id.replace('@s.whatsapp.net', '')
            
            print(f"   Logged in as: {user_name}")
            print(f"   Sender number: {sender_number}")
            print()
            
            # Check configuration
            print("2. Checking configuration...")
            print(f"   Admin phone (receiver): {settings.whatsapp_admin_phone}")
            print()
            
            # Check if same number
            receiver_clean = settings.whatsapp_admin_phone.replace('+', '').replace('@s.whatsapp.net', '')
            sender_clean = sender_number.replace('+', '').replace('@s.whatsapp.net', '')
            
            if sender_clean == receiver_clean:
                print("=" * 70)
                print("⚠️  PROBLEM DETECTED!")
                print("=" * 70)
                print()
                print(f"Sender number: {sender_clean}")
                print(f"Receiver number: {receiver_clean}")
                print()
                print("❌ WhatsApp tidak bisa mengirim pesan ke diri sendiri!")
                print()
                print("SOLUSI:")
                print("1. Logout: curl -X POST http://localhost:3001/logout")
                print("2. Scan QR dengan nomor WhatsApp BERBEDA")
                print("3. ATAU update WHATSAPP_ADMIN_PHONE ke nomor lain di .env")
                print()
                return 1
            else:
                print("=" * 70)
                print("✅ Configuration OK!")
                print("=" * 70)
                print()
                print(f"Sender: {sender_clean}")
                print(f"Receiver: {receiver_clean}")
                print()
                print("Konfigurasi sudah benar - sender dan receiver berbeda.")
                return 0
        else:
            print("   Not connected")
            print()
            print("Run: curl http://localhost:8000/admin/whatsapp/qr -H 'X-Admin-API-Key: xxx'")
            return 1
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
