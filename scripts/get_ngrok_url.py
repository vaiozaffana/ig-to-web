#!/usr/bin/env python
"""
Get ngrok public URL untuk webhook WhatsApp.
Jalankan setelah docker compose up untuk mendapatkan URL webhook.
"""
import sys
import time

import httpx


def get_ngrok_url(max_retries: int = 10) -> str | None:
    """Get public URL from ngrok API."""
    ngrok_api_url = "http://localhost:4040/api/tunnels"
    
    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.get(ngrok_api_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            tunnels = data.get("tunnels", [])
            if not tunnels:
                print(f"Attempt {attempt}/{max_retries}: No tunnels found yet...")
                time.sleep(2)
                continue
            
            # Get first HTTPS tunnel
            for tunnel in tunnels:
                if tunnel.get("proto") == "https":
                    return tunnel.get("public_url")
            
            # Fallback to first tunnel
            return tunnels[0].get("public_url")
        
        except httpx.ConnectError:
            print(f"Attempt {attempt}/{max_retries}: ngrok not ready yet...")
            time.sleep(2)
        except Exception as e:
            print(f"Attempt {attempt}/{max_retries}: Error: {e}")
            time.sleep(2)
    
    return None


def main():
    print("=" * 70)
    print("Fetching ngrok public URL...")
    print("=" * 70)
    print()
    
    url = get_ngrok_url()
    
    if not url:
        print("❌ Failed to get ngrok URL")
        print()
        print("Troubleshooting:")
        print("  1. Pastikan ngrok container berjalan: docker compose ps")
        print("  2. Cek NGROK_AUTHTOKEN sudah diisi di .env")
        print("  3. Cek ngrok logs: docker compose logs ngrok")
        return 1
    
    webhook_url = f"{url}/api/webhooks/whatsapp"
    
    print("✅ Ngrok URL berhasil didapatkan!")
    print()
    print("=" * 70)
    print("WhatsApp Webhook Configuration")
    print("=" * 70)
    print()
    print(f"Webhook URL: {webhook_url}")
    print()
    print("Langkah setup di Meta for Developers:")
    print()
    print("1. Buka https://developers.facebook.com/")
    print("2. Pilih app Anda → WhatsApp → Configuration")
    print("3. Di bagian 'Webhook', klik 'Edit'")
    print("4. Masukkan:")
    print(f"   - Callback URL: {webhook_url}")
    print(f"   - Verify token: [nilai WHATSAPP_VERIFY_TOKEN dari .env Anda]")
    print()
    print("5. Klik 'Verify and Save'")
    print()
    print("6. Subscribe ke webhook fields:")
    print("   - messages (untuk status updates)")
    print()
    print("=" * 70)
    print()
    print(f"🌐 Ngrok Web Interface: http://localhost:4040")
    print("   (untuk monitoring request ke webhook)")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
