#!/bin/bash

# 🚀 AgentMail Demo Quick Start Script

echo "🎯 AgentMail Founding Engineer Demo - Quick Start"
echo "=================================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env_example.txt .env
    echo "⚠️  Please edit .env and add your AgentMail API key!"
    echo "   AGENTMAIL_API_KEY=your_actual_api_key_here"
    echo ""
fi

# Check if logs directory exists
if [ ! -d logs ]; then
    echo "📁 Creating logs directory..."
    mkdir logs
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run system test
echo "🧪 Running system tests..."
python test_system.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ System ready! Next steps:"
    echo "1. Set your AgentMail API key in .env file"
    echo "2. Setup ngrok: brew install ngrok && ngrok http 5000"
    echo "3. Add webhook in AgentMail console"
    echo "4. Start system: python webhook_server.py"
    echo ""
    echo "🎬 Demo endpoints:"
    echo "   - System status: http://localhost:5000/status"
    echo "   - Health check: http://localhost:5000/health"  
    echo "   - Metrics: http://localhost:8000/metrics"
    echo ""
    echo "📖 Read DEMO_GUIDE.md for detailed instructions"
else
    echo "❌ System tests failed. Please check the output above."
fi
