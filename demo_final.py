#!/usr/bin/env python3
"""
🎯 AgentMail Founding Engineer Demo - FINAL VERSION
Ready for live demonstration!
"""

import os
import sys
from webhook_server import WebhookServer

def main():
    print("🎯 AGENTMAIL FOUNDING ENGINEER DEMO - LIVE!")
    print("=" * 55)
    print("🚀 Distributed AI Customer Service System")
    print("🏗️  Featuring: Paxos Consensus + Fault Tolerance + Real-time Processing")
    print("=" * 55)
    
    # Set configuration for demo
    os.environ['AGENTMAIL_API_KEY'] = 'your_actual_api_key_here'  # Replace with real key
    os.environ['WEBHOOK_SECRET'] = 'whsec_hDpFWVvsI17o/4tFVT4XcyIsuHmixK0A'
    os.environ['NODE_ID'] = 'demo-agent-1'
    os.environ['FLASK_PORT'] = '5001'  # Use port 5001 instead
    
    print("🔗 Webhook Configuration (AgentMail Console):")
    print("   ❌ OLD: https://chemigraphically-unmatched-jay.ngrok-free.dev/webhook/agentmail")
    print("   ✅ NEW: https://chemigraphically-unmatched-jay.ngrok-free.dev:5001/webhook/agentmail")
    print("   🔐 Secret: whsec_hDpFWVvsI17o/4tFVT4XcyIsuHmixK0A")
    print("   📧 Events: Message Received ✅, Message Sent ✅")
    
    print("\n📊 Demo Monitoring:")
    print("   🏠 Status: http://localhost:5001/status")
    print("   💚 Health: http://localhost:5001/health") 
    print("   📈 Metrics: http://localhost:8000/metrics")
    print("   🎯 Demo Home: http://localhost:5001/")
    
    print("\n🎬 DEMO SCRIPT:")
    print("1. 📧 Send email to: preciousmanager403@agentmail.to")
    print("2. 📝 Subject: 'Billing Question'")
    print("3. 💬 Body: 'I need help with my invoice'")
    print("4. 👀 Watch: Webhook → Paxos → AI Analysis → Auto Reply")
    
    print("\n⚠️  UPDATE REQUIRED:")
    print("🔧 Update your ngrok webhook URL to port 5001!")
    print("🌐 Run: ngrok http 5001 (in new terminal)")
    
    print("\n" + "=" * 55)
    print("🚀 STARTING DISTRIBUTED SYSTEM...")
    print("=" * 55)
    
    try:
        server = WebhookServer()
        server.run(host='0.0.0.0', port=5001)  # Use port 5001
    except KeyboardInterrupt:
        print("\n\n🎉 Demo completed successfully!")
        print("💪 Distributed systems engineering skills demonstrated!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
