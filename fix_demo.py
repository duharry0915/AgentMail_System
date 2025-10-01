#!/usr/bin/env python3
"""
Fix Demo - Restart with correct ngrok setup
"""

import os
import sys
from webhook_server import WebhookServer

def main():
    print("🔧 FIXING AGENTMAIL DEMO SETUP")
    print("=" * 50)
    
    print("📋 Current Issue Analysis:")
    print("  - ✅ Server running on port 5001")
    print("  - ❌ ngrok still pointing to port 5000")
    print("  - ❌ Webhook URL mismatch")
    
    print("\n🛠️  SOLUTION:")
    print("1. Keep server on port 5000 (standard)")
    print("2. Use existing ngrok tunnel")
    print("3. Use correct webhook URL")
    
    print("\n🔗 CORRECT Webhook Configuration:")
    print("   URL: https://chemigraphically-unmatched-jay.ngrok-free.dev/webhook/agentmail")
    print("   Secret: whsec_hDpFWVvsI17o/4tFVT4XcyIsuHmixK0A")
    print("   Events: Message Received ✅, Message Sent ✅")
    
    print("\n🚀 Starting server on PORT 5000...")
    print("=" * 50)
    
    # Set configuration for demo
    os.environ['AGENTMAIL_API_KEY'] = 'your_actual_api_key_here'  # Replace with real key
    os.environ['WEBHOOK_SECRET'] = 'whsec_hDpFWVvsI17o/4tFVT4XcyIsuHmixK0A'
    os.environ['NODE_ID'] = 'demo-agent-1'
    os.environ['FLASK_PORT'] = '5000'  # Back to port 5000
    
    try:
        server = WebhookServer()
        # Force use port 5000 to match ngrok
        server.run(host='0.0.0.0', port=5000)
    except OSError as e:
        if "Address already in use" in str(e):
            print("\n❌ Port 5000 still in use!")
            print("🔧 SOLUTION: Disable AirPlay Receiver")
            print("   1. System Preferences → General → AirDrop & Handoff")
            print("   2. Turn OFF 'AirPlay Receiver'")
            print("   3. Restart this script")
        else:
            print(f"❌ Error: {e}")
    except KeyboardInterrupt:
        print("\n🎉 Demo ended!")

if __name__ == "__main__":
    main()
