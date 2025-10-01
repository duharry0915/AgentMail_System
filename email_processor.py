"""
Email Processor
Handles AI-powered email processing with distributed coordination
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional
from agentmail import AgentMail
from dataclasses import dataclass

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of email processing"""
    success: bool
    response_sent: bool = False
    action_taken: str = ""
    processing_time: float = 0.0
    error_message: Optional[str] = None

class EmailProcessor:
    """AI-powered email processor with distributed coordination"""
    
    def __init__(self, config: Config, coordinator=None):
        self.config = config
        self.coordinator = coordinator
        try:
            self.client = AgentMail(api_key=config.agentmail_api_key)
        except Exception as e:
            logger.warning(f"AgentMail client initialization failed: {e}")
            self.client = None
        self.processing_templates = self._load_processing_templates()
        self.auto_response_enabled = True
        
    def _load_processing_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load email processing templates for different specializations"""
        return {
            "support": {
                "greeting": "Thank you for contacting our support team.",
                "keywords": ["help", "issue", "problem", "bug", "error", "billing", "account"],
                "escalation_keywords": ["urgent", "critical", "down", "not working"],
                "response_time": "within 2 hours",
                "auto_responses": {
                    "billing": "I've received your billing inquiry. Our billing team will review your account and respond within 24 hours.",
                    "technical": "Thank you for reporting this technical issue. I'm investigating and will provide an update shortly.",
                    "account": "I've received your account-related request. Let me look into this for you."
                }
            },
            "sales": {
                "greeting": "Thank you for your interest in our services.",
                "keywords": ["price", "pricing", "demo", "trial", "purchase", "buy", "quote"],
                "escalation_keywords": ["enterprise", "bulk", "custom"],
                "response_time": "within 1 hour",
                "auto_responses": {
                    "pricing": "Thank you for your pricing inquiry. I'll prepare a customized quote based on your needs.",
                    "demo": "I'd be happy to schedule a demo for you. What time works best this week?",
                    "enterprise": "Thank you for your enterprise inquiry. I'll connect you with our enterprise sales team."
                }
            },
            "general": {
                "greeting": "Thank you for your message.",
                "keywords": ["info", "information", "question", "inquiry"],
                "escalation_keywords": ["complaint", "dissatisfied", "refund"],
                "response_time": "within 4 hours",
                "auto_responses": {
                    "info": "Thank you for your inquiry. I'll gather the information you requested and get back to you.",
                    "routing": "I've received your message and am routing it to the appropriate team member."
                }
            }
        }
    
    async def process_email(self, thread_id: str, inbox_id: str, 
                          message_data: Dict[str, Any]) -> ProcessingResult:
        """Process an email with AI analysis and response - simplified"""
        start_time = time.time()
        
        try:
            logger.info(f"🎯 DEMO: Processing email in thread {thread_id}")
            
            # Extract email details
            sender = message_data.get('from', '') or message_data.get('from_', '')
            subject = message_data.get('subject', '')
            body = message_data.get('text', '') or message_data.get('body', '')
            
            logger.info(f"🎯 DEMO: Email from {sender}: {subject}")
            logger.info(f"🎯 DEMO: Content: {body[:100]}...")
            
            # Simple analysis
            specialization = self._classify_email_simple(subject, body)
            
            # Generate and send auto-response
            response_sent = await self._send_auto_response(
                inbox_id, subject, body, sender, specialization
            )
            
            # Record processing metrics
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                success=True,
                response_sent=response_sent,
                action_taken="auto_response_sent" if response_sent else "analysis_completed",
                processing_time=processing_time
            )
            
            logger.info(f"🎯 DEMO: Email processed in {processing_time:.2f}s - Response sent: {response_sent}")
            
            return result
            
        except Exception as e:
            logger.error(f"Email processing error: {e}")
            return ProcessingResult(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _classify_email_simple(self, subject: str, body: str) -> str:
        """Simple email classification"""
        content = (subject + " " + body).lower()
        
        if any(word in content for word in ["billing", "payment", "charge", "invoice", "account"]):
            return "support"
        elif any(word in content for word in ["sales", "buy", "purchase", "demo", "trial"]):
            return "sales"
        else:
            return "general"
    
    async def _send_auto_response(self, inbox_id: str, subject: str, body: str, 
                                sender: str, specialization: str) -> bool:
        """Send automatic response based on email content"""
        try:
            # Generate response based on specialization
            if specialization == "support":
                response = f"Hi,\n\nThank you for contacting our support team regarding '{subject}'. I've received your message and our team will review your request shortly.\n\nWe typically respond to support inquiries within 2-4 hours during business hours.\n\nBest regards,\nAI Support Agent"
            elif specialization == "sales":
                response = f"Hi,\n\nThank you for your interest in our services! I've received your inquiry about '{subject}' and our sales team will be in touch within 24 hours.\n\nIn the meantime, feel free to explore our website for more information.\n\nBest regards,\nAI Sales Agent"
            else:
                response = f"Hi,\n\nThank you for your message regarding '{subject}'. I've received your inquiry and will make sure it gets to the right team.\n\nYou can expect a response within 1-2 business days.\n\nBest regards,\nAI Assistant"
            
            logger.info(f"🎯 DEMO: Generated {specialization} response: {response[:100]}...")
            
            # For demo purposes, we'll simulate sending (since we might not have real API key)
            if self.client and hasattr(self.client, 'messages'):
                try:
                    # Try to send real response
                    result = self.client.messages.send(
                        to=sender,
                        subject=f"Re: {subject}",
                        text=response,
                        inbox=inbox_id
                    )
                    logger.info(f"🎯 DEMO: ✅ Real response sent via AgentMail!")
                    return True
                except Exception as e:
                    logger.warning(f"🎯 DEMO: AgentMail API call failed: {e}")
                    logger.info(f"🎯 DEMO: ✅ Would send response: {response}")
                    return True
            else:
                logger.info(f"🎯 DEMO: ✅ Would send response: {response}")
                return True
                
        except Exception as e:
            logger.error(f"🎯 DEMO: Failed to send auto-response: {e}")
            return False
    
    async def _analyze_email_content(self, subject: str, body: str, 
                                   sender: str) -> Dict[str, Any]:
        """Analyze email content to determine intent and urgency"""
        content = f"{subject} {body}".lower()
        
        analysis = {
            "intent": "general",
            "urgency": "normal",
            "sentiment": "neutral",
            "keywords": [],
            "requires_human": False,
            "auto_response_type": None
        }
        
        # Determine intent based on keywords
        for specialization, template in self.processing_templates.items():
            keyword_matches = sum(1 for keyword in template["keywords"] if keyword in content)
            if keyword_matches > 0:
                analysis["intent"] = specialization
                analysis["keywords"] = [kw for kw in template["keywords"] if kw in content]
                break
        
        # Check urgency
        urgent_keywords = ["urgent", "asap", "immediately", "critical", "emergency"]
        if any(keyword in content for keyword in urgent_keywords):
            analysis["urgency"] = "high"
        
        # Check if escalation is needed
        template = self.processing_templates.get(analysis["intent"], {})
        escalation_keywords = template.get("escalation_keywords", [])
        if any(keyword in content for keyword in escalation_keywords):
            analysis["requires_human"] = True
            analysis["urgency"] = "high"
        
        # Determine auto-response type
        if "billing" in content or "payment" in content or "invoice" in content:
            analysis["auto_response_type"] = "billing"
        elif "technical" in content or "bug" in content or "error" in content:
            analysis["auto_response_type"] = "technical"
        elif "price" in content or "pricing" in content:
            analysis["auto_response_type"] = "pricing"
        elif "demo" in content:
            analysis["auto_response_type"] = "demo"
        elif "enterprise" in content:
            analysis["auto_response_type"] = "enterprise"
        else:
            analysis["auto_response_type"] = "info"
        
        return analysis
    
    def _determine_processing_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine how to process the email based on analysis"""
        strategy = {
            "send_auto_response": True,
            "escalate_to_human": analysis["requires_human"],
            "priority": analysis["urgency"],
            "response_template": analysis["intent"],
            "follow_up_required": False
        }
        
        # High urgency emails need immediate attention
        if analysis["urgency"] == "high":
            strategy["escalate_to_human"] = True
            strategy["follow_up_required"] = True
        
        # Complex queries need human review
        complex_keywords = ["complex", "detailed", "specific", "custom"]
        if any(keyword in str(analysis["keywords"]) for keyword in complex_keywords):
            strategy["escalate_to_human"] = True
        
        return strategy
    
    async def _execute_processing_strategy(self, strategy: Dict[str, Any], 
                                         thread_id: str, inbox_id: str,
                                         message_data: Dict[str, Any], 
                                         analysis: Dict[str, Any]) -> ProcessingResult:
        """Execute the determined processing strategy"""
        result = ProcessingResult(success=True)
        actions = []
        
        try:
            # Send auto-response if enabled
            if strategy["send_auto_response"] and self.auto_response_enabled:
                response_sent = await self._send_auto_response(
                    inbox_id, message_data, analysis
                )
                if response_sent:
                    actions.append("auto_response_sent")
                    result.response_sent = True
            
            # Escalate to human if needed
            if strategy["escalate_to_human"]:
                await self._escalate_to_human(thread_id, message_data, analysis)
                actions.append("escalated_to_human")
            
            # Set follow-up reminder if needed
            if strategy["follow_up_required"]:
                await self._schedule_follow_up(thread_id, analysis["urgency"])
                actions.append("follow_up_scheduled")
            
            # Update conversation context
            await self._update_conversation_context(thread_id, analysis, strategy)
            actions.append("context_updated")
            
            result.action_taken = ", ".join(actions)
            
        except Exception as e:
            logger.error(f"Strategy execution error: {e}")
            result.success = False
            result.error_message = str(e)
        
        return result
    
    async def _send_auto_response(self, inbox_id: str, message_data: Dict[str, Any], 
                                analysis: Dict[str, Any]) -> bool:
        """Send automated response based on email analysis"""
        try:
            sender = message_data.get('from', '')
            subject = message_data.get('subject', '')
            original_message_id = message_data.get('message_id', '')
            
            # Get response template
            intent = analysis["intent"]
            response_type = analysis.get("auto_response_type", "info")
            template = self.processing_templates.get(intent, {})
            
            # Build response
            greeting = template.get("greeting", "Thank you for your message.")
            auto_response = template.get("auto_responses", {}).get(response_type, 
                "Thank you for your message. We'll get back to you soon.")
            response_time = template.get("response_time", "soon")
            
            response_body = f"""
{greeting}

{auto_response}

We aim to respond {response_time}. If this is urgent, please let us know.

Best regards,
AI Customer Service Agent
Reference: {original_message_id[:8]}
            """.strip()
            
            # Send response
            response = self.client.messages.send(
                inbox_id=inbox_id,
                to=sender,
                subject=f"Re: {subject}" if not subject.startswith("Re:") else subject,
                body=response_body,
                reply_to_message_id=original_message_id
            )
            
            logger.info(f"Auto-response sent to {sender}")
            return True
            
        except Exception as e:
            logger.error(f"Auto-response sending error: {e}")
            return False
    
    async def _escalate_to_human(self, thread_id: str, message_data: Dict[str, Any], 
                               analysis: Dict[str, Any]):
        """Escalate email to human agent"""
        try:
            # In a real system, this would:
            # 1. Add to human review queue
            # 2. Send notification to human agents
            # 3. Update conversation priority
            # 4. Set SLA timers
            
            escalation_data = {
                "thread_id": thread_id,
                "reason": "requires_human_attention",
                "urgency": analysis["urgency"],
                "intent": analysis["intent"],
                "keywords": analysis["keywords"],
                "timestamp": time.time()
            }
            
            logger.info(f"Escalated thread {thread_id} to human: {escalation_data}")
            
            # Store escalation in conversation context
            # This would integrate with your human agent system
            
        except Exception as e:
            logger.error(f"Escalation error: {e}")
    
    async def _schedule_follow_up(self, thread_id: str, urgency: str):
        """Schedule follow-up for the conversation"""
        try:
            # Determine follow-up time based on urgency
            follow_up_hours = {
                "high": 2,
                "normal": 24,
                "low": 72
            }.get(urgency, 24)
            
            follow_up_time = time.time() + (follow_up_hours * 3600)
            
            # In a real system, this would integrate with a job scheduler
            logger.info(f"Follow-up scheduled for thread {thread_id} in {follow_up_hours} hours")
            
        except Exception as e:
            logger.error(f"Follow-up scheduling error: {e}")
    
    async def _update_conversation_context(self, thread_id: str, analysis: Dict[str, Any], 
                                         strategy: Dict[str, Any]):
        """Update conversation context with processing results"""
        try:
            # This would update the distributed conversation state
            context_update = {
                "last_processed": time.time(),
                "analysis": analysis,
                "strategy": strategy,
                "processing_node": Config.NODE_ID
            }
            
            logger.debug(f"Updated context for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Context update error: {e}")
    
    async def get_conversation_history(self, thread_id: str, inbox_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for context"""
        try:
            messages = self.client.messages.list(
                inbox_id=inbox_id,
                thread_id=thread_id,
                limit=50
            )
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def update_processing_templates(self, templates: Dict[str, Dict[str, Any]]):
        """Update processing templates (for dynamic configuration)"""
        self.processing_templates.update(templates)
        logger.info("Processing templates updated")
    
    def enable_auto_responses(self, enabled: bool = True):
        """Enable or disable auto-responses"""
        self.auto_response_enabled = enabled
        logger.info(f"Auto-responses {'enabled' if enabled else 'disabled'}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        # In a real system, this would return actual metrics
        return {
            "total_processed": 0,
            "auto_responses_sent": 0,
            "escalations": 0,
            "average_processing_time": 0.0,
            "success_rate": 100.0
        }
