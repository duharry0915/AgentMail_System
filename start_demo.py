#!/usr/bin/env python3
"""
AgentMail Demo Starter
Configured for your specific webhook setup
"""

import os
import sys
from webhook_server import WebhookServer

def main():
    print("🎯 AGENTMAIL FOUNDING ENGINEER DEMO")
    print("=" * 50)
    print("🚀 Distributed AI Customer Service System")
    print("=" * 50)
    
    # Set configuration
    os.environ['AGENTMAIL_API_KEY'] = 'your_actual_api_key_here'  # You'll replace this
    os.environ['WEBHOOK_SECRET'] = 'whsec_hDpFWVvsI17o/4tFVT4XcyIsuHmixK0A'
    os.environ['NODE_ID'] = 'demo-agent-1'
    
    print("🔗 Webhook Configuration:")
    print("   URL: https://chemigraphically-unmatched-jay.ngrok-free.dev/webhook/agentmail")
    print("   Secret: whsec_hDpFWVvsI17o/4tFVT4XcyIsuHmixK0A")
    print("   Events: ✅ Message Received, ✅ Message Sent")
    
    print("\n📊 Monitoring Endpoints:")
    print("   Status: http://localhost:5000/status")
    print("   Health: http://localhost:5000/health") 
    print("   Metrics: http://localhost:8000/metrics")
    
    print("\n🎬 Demo Ready!")
    print("Send emails to your AgentMail inboxes to see the system in action!")
    print("=" * 50)
    
    try:
        server = WebhookServer()
        server.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Demo ended. Thanks for watching!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Tip: Make sure port 5000 is available")

if __name__ == "__main__":
    main()
