"""
Flask Webhook Server
Receives AgentMail webhook events and coordinates distributed email processing
"""

import asyncio
import json
import logging
import threading
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
from typing import Dict, Any

from config import Config, setup_logging
from agent_coordinator import coordinator, PaxosMessage, MessageType
from email_processor import EmailProcessor

# Setup logging
logger = setup_logging()
config = Config()

# Prometheus metrics
webhook_requests_total = Counter('webhook_requests_total', 'Total webhook requests', ['event_type', 'status'])
webhook_duration = Histogram('webhook_processing_duration_seconds', 'Webhook processing duration')
active_conversations = Gauge('active_conversations_total', 'Number of active conversations')
agent_assignments = Counter('agent_assignments_total', 'Total agent assignments', ['agent_id', 'specialization'])
consensus_operations = Counter('consensus_operations_total', 'Total consensus operations', ['operation', 'result'])

class WebhookServer:
    """Flask server handling AgentMail webhooks and Paxos communication"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.email_processor = EmailProcessor(config, coordinator)
        self.setup_routes()
        self.event_loop = None
        self.loop_thread = None
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/webhook/agentmail', methods=['POST'])
        def handle_agentmail_webhook():
            """Handle AgentMail webhook events"""
            start_time = time.time()
            
            try:
                # Validate request
                if not request.is_json:
                    webhook_requests_total.labels(event_type='unknown', status='error').inc()
                    return jsonify({'error': 'Content-Type must be application/json'}), 400
                
                event_data = request.get_json()
                event_type = event_data.get('type', 'unknown')
                
                logger.info(f"🎯 DEMO: Received webhook event: {event_type}")
                logger.info(f"🎯 DEMO: Full event data: {json.dumps(event_data, indent=2)}")
                
                # Process event asynchronously
                if self.event_loop and not self.event_loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._process_webhook_event(event_data),
                        self.event_loop
                    )
                
                # Record metrics
                duration = time.time() - start_time
                webhook_duration.observe(duration)
                webhook_requests_total.labels(event_type=event_type, status='success').inc()
                
                return jsonify({'status': 'received', 'event_type': event_type}), 200
                
            except Exception as e:
                logger.error(f"Webhook processing error: {e}")
                webhook_requests_total.labels(event_type='unknown', status='error').inc()
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/paxos', methods=['POST'])
        def handle_paxos_message():
            """Handle Paxos consensus messages"""
            try:
                if not request.is_json:
                    return jsonify({'error': 'Content-Type must be application/json'}), 400
                
                message_data = request.get_json()
                message = PaxosMessage(**message_data)
                
                logger.debug(f"Received Paxos message: {message.msg_type.value} from {message.sender}")
                
                # Handle message through coordinator
                response = coordinator.paxos.handle_paxos_message(message)
                
                if response:
                    consensus_operations.labels(
                        operation=message.msg_type.value, 
                        result='success'
                    ).inc()
                    return jsonify(response.__dict__), 200
                else:
                    consensus_operations.labels(
                        operation=message.msg_type.value, 
                        result='rejected'
                    ).inc()
                    return jsonify({'status': 'rejected'}), 400
                    
            except Exception as e:
                logger.error(f"Paxos message handling error: {e}")
                consensus_operations.labels(operation='unknown', result='error').inc()
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/heartbeat', methods=['POST'])
        def handle_heartbeat():
            """Handle agent heartbeat messages"""
            try:
                if not request.is_json:
                    return jsonify({'error': 'Content-Type must be application/json'}), 400
                
                heartbeat_data = request.get_json()
                agent_id = heartbeat_data.get('agent_id')
                agent_info = heartbeat_data.get('info', {})
                
                if not agent_id:
                    return jsonify({'error': 'agent_id required'}), 400
                
                coordinator.handle_heartbeat(agent_id, agent_info)
                
                return jsonify({'status': 'received'}), 200
                
            except Exception as e:
                logger.error(f"Heartbeat handling error: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_system_status():
            """Get current system status"""
            try:
                status = coordinator.get_system_status()
                active_conversations.set(status.get('conversations', 0))
                return jsonify(status), 200
            except Exception as e:
                logger.error(f"Status retrieval error: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/metrics', methods=['GET'])
        def get_metrics():
            """Prometheus metrics endpoint"""
            return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'node_id': Config.NODE_ID,
                'timestamp': time.time()
            }), 200
    
    async def _process_webhook_event(self, event_data: Dict[str, Any]):
        """Process webhook event asynchronously"""
        try:
            event_type = event_data.get('type')
            
            if event_type == 'message.received':
                await self._handle_message_received(event_data)
            elif event_type == 'message.sent':
                await self._handle_message_sent(event_data)
            elif event_type == 'thread.created':
                await self._handle_thread_created(event_data)
            elif event_type == 'event':
                # Handle AgentMail's generic 'event' type
                await self._handle_generic_event(event_data)
            else:
                logger.warning(f"🎯 DEMO: Unhandled event type: {event_type}")
                logger.info(f"🎯 DEMO: Event data: {json.dumps(event_data, indent=2)}")
                
        except Exception as e:
            logger.error(f"Event processing error: {e}")
    
    async def _handle_message_received(self, event_data: Dict[str, Any]):
        """Handle incoming message event"""
        try:
            message_data = event_data.get('data', {})
            thread_id = message_data.get('thread_id')
            inbox_id = message_data.get('inbox_id')
            sender = message_data.get('from') or message_data.get('from_')
            subject = message_data.get('subject', '')
            body = message_data.get('text', '') or message_data.get('body', '')
            message_id = message_data.get('message_id', '')
            
            if not thread_id:
                logger.error("🎯 DEMO: Message received without thread_id")
                return
            
            logger.info(f"🎯 DEMO: Processing message in thread {thread_id}")
            logger.info(f"🎯 DEMO: From: {sender}")
            logger.info(f"🎯 DEMO: Subject: {subject}")
            logger.info(f"🎯 DEMO: Body preview: {body[:100]}...")
            
            # Assign agent using distributed consensus
            logger.info("🎯 DEMO: Starting Paxos consensus for agent assignment...")
            assigned_agent = await coordinator.assign_agent_for_email(
                thread_id=thread_id,
                email_content=f"{subject}\n{body}",
                sender=sender
            )
            
            if assigned_agent:
                logger.info(f"🎯 DEMO: Paxos consensus completed! Agent {assigned_agent} assigned")
                
                # Record assignment metrics
                conversation_state = coordinator.conversations.get(thread_id)
                specialization = conversation_state.context.get('specialization', 'unknown') if conversation_state else 'unknown'
                agent_assignments.labels(agent_id=assigned_agent, specialization=specialization).inc()
                
                logger.info(f"🎯 DEMO: Email classified as: {specialization}")
                
                # Process email if this node is the assigned agent
                if assigned_agent == Config.NODE_ID:
                    logger.info("🎯 DEMO: This node is the assigned agent - processing email with AI...")
                    result = await self.email_processor.process_email(
                        thread_id=thread_id,
                        inbox_id=inbox_id,
                        message_data=message_data
                    )
                    
                    if result.success:
                        logger.info(f"🎯 DEMO: AI processing completed! Action: {result.action_taken}")
                        if result.response_sent:
                            logger.info("🎯 DEMO: ✅ Auto-response sent successfully!")
                    else:
                        logger.error(f"🎯 DEMO: AI processing failed: {result.error_message}")
                else:
                    logger.info(f"🎯 DEMO: Message assigned to different agent: {assigned_agent}")
            else:
                logger.error(f"🎯 DEMO: ❌ Failed to reach consensus for thread {thread_id}")
                
        except Exception as e:
            logger.error(f"🎯 DEMO: Message received handling error: {e}")
    
    async def _handle_message_sent(self, event_data: Dict[str, Any]):
        """Handle message sent event"""
        try:
            message_data = event_data.get('data', {})
            thread_id = message_data.get('thread_id')
            
            logger.info(f"Message sent in thread {thread_id}")
            
            # Update conversation state if we're managing this thread
            if thread_id in coordinator.conversations:
                state = coordinator.conversations[thread_id]
                state.context['last_sent'] = time.time()
                state.last_updated = time.time()
                state.version += 1
                
        except Exception as e:
            logger.error(f"Message sent handling error: {e}")
    
    async def _handle_thread_created(self, event_data: Dict[str, Any]):
        """Handle thread created event"""
        try:
            thread_data = event_data.get('data', {})
            thread_id = thread_data.get('thread_id')
            
            logger.info(f"New thread created: {thread_id}")
            
        except Exception as e:
            logger.error(f"Thread created handling error: {e}")
    
    async def _handle_generic_event(self, event_data: Dict[str, Any]):
        """Handle AgentMail's generic 'event' type"""
        try:
            # AgentMail sends event_type within the event wrapper
            real_event_type = event_data.get('event_type')
            message_data = event_data.get('message', {})
            
            logger.info(f"🎯 DEMO: Processing generic event with real type: {real_event_type}")
            
            # Check the actual event type
            if real_event_type == 'message.received':
                logger.info("🎯 DEMO: Detected message.received - triggering full AI processing!")
                # Create proper event structure for message handling
                processed_event = {
                    'type': 'message.received',
                    'data': message_data
                }
                await self._handle_message_received(processed_event)
                
            elif real_event_type == 'message.sent':
                logger.info("🎯 DEMO: Detected message.sent")
                processed_event = {
                    'type': 'message.sent', 
                    'data': message_data
                }
                await self._handle_message_sent(processed_event)
                
            else:
                logger.info(f"🎯 DEMO: Unhandled event type: {real_event_type}")
                
        except Exception as e:
            logger.error(f"🎯 DEMO: Generic event handling error: {e}")
    
    def start_event_loop(self):
        """Start asyncio event loop in separate thread"""
        def run_loop():
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            
            # Start coordinator
            self.event_loop.run_until_complete(coordinator.start())
            
            # Keep loop running
            self.event_loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        
        # Wait for loop to be ready
        while self.event_loop is None:
            time.sleep(0.1)
    
    def stop_event_loop(self):
        """Stop asyncio event loop"""
        if self.event_loop and not self.event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(coordinator.stop(), self.event_loop)
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
    
    def run(self, host: str = None, port: int = None, debug: bool = False):
        """Run the Flask server"""
        host = host or Config.FLASK_HOST
        port = port or Config.FLASK_PORT
        debug = debug or Config.FLASK_DEBUG
        
        # Start event loop
        self.start_event_loop()
        
        try:
            logger.info(f"Starting webhook server on {host}:{port}")
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        finally:
            self.stop_event_loop()

def create_app():
    """Create Flask app for WSGI deployment"""
    server = WebhookServer()
    server.start_event_loop()
    return server.app

if __name__ == '__main__':
    # Create logs directory
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Start server
    server = WebhookServer()
    server.run()
