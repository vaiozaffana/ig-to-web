#!/usr/bin/env python
"""
Test WhatsApp webhook verification dan POST endpoint.
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.settings import settings


def test_verification():
    """Test webhook verification (GET request)."""
    print("=" * 70)
    print("Testing WhatsApp Webhook Verification (GET)")
    print("=" * 70)
    print()
    
    url = "http://localhost:8000/api/webhooks/whatsapp"
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": settings.whatsapp_verify_token,
        "hub.challenge": "test-challenge-from-meta"
    }
    
    print(f"URL: {url}")
    print(f"Verify Token: {settings.whatsapp_verify_token[:20]}...")
    print()
    
    try:
        response = httpx.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            if response.text == "test-challenge-from-meta":
                print("✅ Verification SUCCESS!")
                print(f"Response: {response.text}")
                return True
            else:
                print("❌ Verification FAILED!")
                print(f"Expected: test-challenge-from-meta")
                print(f"Got: {response.text}")
                return False
        else:
            print(f"❌ Verification FAILED with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_webhook_post():
    """Test webhook POST endpoint."""
    print()
    print("=" * 70)
    print("Testing WhatsApp Webhook POST")
    print("=" * 70)
    print()
    
    url = "http://localhost:8000/api/webhooks/whatsapp"
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15551234567",
                        "phone_number_id": settings.whatsapp_phone_number_id
                    },
                    "statuses": [{
                        "id": "wamid.test123",
                        "status": "sent",
                        "timestamp": "1683748521",
                        "recipient_id": "628979755323"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    print(f"URL: {url}")
    print(f"Payload: message status update (sent)")
    print()
    
    try:
        response = httpx.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print("✅ Webhook POST SUCCESS!")
                print(f"Response: {data}")
                return True
            else:
                print("❌ Webhook POST returned unexpected response")
                print(f"Response: {data}")
                return False
        else:
            print(f"❌ Webhook POST FAILED with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    if not settings.whatsapp_verify_token:
        print("❌ WHATSAPP_VERIFY_TOKEN not configured in .env")
        return 1
    
    verification_ok = test_verification()
    post_ok = test_webhook_post()
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Verification: {'✅ PASS' if verification_ok else '❌ FAIL'}")
    print(f"POST Webhook: {'✅ PASS' if post_ok else '❌ FAIL'}")
    print()
    
    if verification_ok and post_ok:
        print("✅ All webhook tests passed!")
        print()
        print("Next steps:")
        print("  1. Start ngrok: docker compose up -d ngrok")
        print("  2. Get webhook URL: make ngrok-url")
        print("  3. Setup di Meta for Developers console")
        return 0
    else:
        print("❌ Some tests failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
