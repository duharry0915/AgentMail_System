#!/usr/bin/env python3
"""
Final Webhook Setup for AgentMail Demo
Validates configuration and provides exact webhook URL
"""

import os
import sys
from dotenv import load_dotenv

def main():
    print("🔧 AgentMail Webhook Final Setup")
    print("=" * 40)
    
    load_dotenv()
    
    # Check API key
    api_key = os.getenv('AGENTMAIL_API_KEY')
    if not api_key or api_key == 'your_agentmail_api_key_here':
        print("❌ Please update your .env file with the actual API key")
        print("Edit .env file and replace with:")
        print("AGENTMAIL_API_KEY=am_0f11c••••••••••••••")  # Use your actual key
        return
    
    print("✅ API Key configured")
    
    # Provide exact webhook configuration
    print("\n📡 Webhook Configuration for AgentMail Console:")
    print("=" * 50)
    print("🔗 Endpoint URL:")
    print("https://chemigraphically-unmatched-jay.ngrok-free.dev/webhook/agentmail")
    print("                                                    ^^^^^^^^^^^^^^^^^^^")
    print("                                                    Add this path!")
    print("\n📋 Events to select:")
    print("✅ Message Received")
    print("✅ Message Sent")
    print("⚪ Message Delivered (optional)")
    print("⚪ Message Bounced (optional)")
    
    print("\n🔐 Security:")
    print("✅ Let AgentMail auto-generate the secret")
    print("✅ Our system will handle signature verification")
    
    print("\n📝 Optional Fields:")
    print("Inbox IDs: (leave empty for all inboxes)")
    print("Client ID: distributed-ai-demo")
    
    print("\n🚀 After creating webhook:")
    print("1. Start system: python webhook_server.py")
    print("2. Send test email to your inbox")
    print("3. Watch the magic happen!")
    
    print("\n✨ Ready to impress AgentMail!")

if __name__ == "__main__":
    main()
