#!/usr/bin/env python3
"""
简化的 AgentMail webhook 服务器 - 纯粹的自动回复功能
"""

import os
import json
import time
import re
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# OpenAI for AI-powered responses
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))
    openai_available = bool(os.getenv('OPENAI_API_KEY'))
except:
    openai_client = None
    openai_available = False

# 配置
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')
AGENTMAIL_API_KEY = os.getenv('AGENTMAIL_API_KEY', '')
SEND_REAL = os.getenv('SEND_REAL', '1') in ('1', 'true', 'True')  # 默认启用真实发送

app = Flask(__name__)

# Optional AgentMail client
try:
    from agentmail import AgentMail  # type: ignore
    agentmail_available = True
except Exception:
    AgentMail = None  # type: ignore
    agentmail_available = False

client = None
print("=" * 60)
print("AGENTMAIL AI AUTO-REPLY SERVICE")
print("=" * 60)
print(f"[INIT] AgentMail SDK: {'Available' if agentmail_available else 'Not Available'}")
print(f"[INIT] OpenAI Integration: {'Enabled' if openai_available else 'Disabled'}")

if agentmail_available and AGENTMAIL_API_KEY and AGENTMAIL_API_KEY != 'your_actual_api_key_here':
    try:
        client = AgentMail(api_key=AGENTMAIL_API_KEY)
        print("[INIT] AgentMail client initialized successfully")
    except Exception as e:
        print(f"[ERROR] AgentMail client initialization failed: {e}")
        client = None
else:
    if not agentmail_available:
        print("[WARN] AgentMail package not available - using simulation mode")
    else:
        print("[WARN] AGENTMAIL_API_KEY not set - using simulation mode")

def classify_email(subject, body):
    """
    Analyze email content to determine which specialized agent should handle it.
    
    Categories:
    - 'billing': Financial and payment-related inquiries
    - 'technical': Technical issues, bugs, errors
    - 'general': All other inquiries
    """
    content = (subject + " " + body).lower()
    
    # Billing agent keywords
    billing_keywords = [
        "bill", "invoice", "payment", "refund", "charge", 
        "subscription", "pricing", "account", "receipt", "cost"
    ]
    
    # Technical agent keywords
    technical_keywords = [
        "error", "bug", "crash", "not working", "500", "api", 
        "broken", "issue", "down", "fail", "problem", "debug"
    ]
    
    # Check for billing-related content
    if any(word in content for word in billing_keywords):
        return "billing"
    
    # Check for technical-related content
    elif any(word in content for word in technical_keywords):
        return "technical"
    
    # Default to general agent
    else:
        return "general"


def get_agent_system_prompt(agent_type):
    """
    Return specialized system prompts for different agent types.
    
    Args:
        agent_type: One of 'billing', 'technical', or 'general'
    
    Returns:
        str: System prompt tailored to the agent's specialty
    """
    prompts = {
        "billing": (
            "You are a professional billing specialist at AgentMail. Be helpful and empathetic. "
            "Provide clear explanations about charges, refunds, and payment procedures. "
            "Always maintain a patient and understanding tone when discussing financial matters. "
            "Sign your emails as 'AgentMail Billing Team' without any placeholder names."
        ),
        "technical": (
            "You are a senior technical support engineer at AgentMail. Provide step-by-step debugging "
            "guidance and technical solutions. Be precise and thorough. Use technical terminology "
            "when appropriate, but explain complex concepts clearly. "
            "Sign your emails as 'AgentMail Technical Support' without any placeholder names."
        ),
        "general": (
            "You are a friendly customer service representative at AgentMail. Be warm, helpful, and professional. "
            "Provide excellent customer service and make the customer feel valued and heard. "
            "Sign your emails as 'AgentMail Support Team' without any placeholder names."
        )
    }
    
    return prompts.get(agent_type, prompts["general"])

def generate_ai_response(subject, body, sender, agent_type):
    """
    Generate AI-powered email response using the appropriate specialized agent.
    
    Args:
        subject: Email subject line
        body: Email body content
        sender: Sender email address
        agent_type: Type of agent ('billing', 'technical', or 'general')
    
    Returns:
        str: AI-generated response text
    """
    if openai_available and openai_client:
        try:
            # Get specialized system prompt for the agent type
            system_prompt = get_agent_system_prompt(agent_type)
            
            # Construct user prompt with email context
            user_prompt = f"""Please respond to this customer email:

Subject: {subject}
From: {sender}

Email Content:
{body}

Generate a brief, helpful response (2-3 sentences). Be professional and address their specific concern. 
Do not use placeholder text like [Your Name] - use the proper team signature specified in your role."""

            # Call OpenAI with agent-specific system prompt
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[WARN] OpenAI API call failed: {e}")
            print("[INFO] Falling back to template response")
            return generate_template_response(subject, agent_type)
    else:
        print("[INFO] OpenAI not available - using template response")
        return generate_template_response(subject, agent_type)

def generate_template_response(subject, agent_type):
    """
    Generate template-based response as fallback when OpenAI is unavailable.
    
    Args:
        subject: Email subject
        agent_type: Type of agent ('billing', 'technical', or 'general')
    
    Returns:
        str: Template-based response
    """
    templates = {
        "billing": f"Hi,\n\nThank you for contacting our billing department regarding '{subject}'. I've received your inquiry and our billing specialist will review your request and respond within 24 hours.\n\nBest regards,\nBilling Support Team",
        
        "technical": f"Hi,\n\nThank you for reporting this technical issue regarding '{subject}'. I've received your report and our technical team will investigate and provide a solution shortly.\n\nBest regards,\nTechnical Support Team",
        
        "general": f"Hi,\n\nThank you for your message regarding '{subject}'. I've received your inquiry and will make sure it gets to the appropriate team for assistance.\n\nBest regards,\nCustomer Service Team"
    }
    
    return templates.get(agent_type, templates["general"])


def extract_email(address: str) -> str:
    """Extract plain email from 'Name <email@x>' or return as-is."""
    if not address:
        return address
    m = re.search(r"<([^>]+)>", address)
    return m.group(1) if m else address.strip()

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': time.time(),
        'service': 'AgentMail AI Auto-Reply'
    }), 200

@app.route('/webhook/agentmail', methods=['POST'])
def handle_webhook():
    """Handle AgentMail webhook events"""
    try:
        if not request.is_json:
            print("[ERROR] Invalid content type - expected JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        event_data = request.get_json()
        event_type = event_data.get('type', 'unknown')
        
        # Process different event formats
        processed = False
        
        # Format 1: type = 'event' with nested event_type
        if event_type == 'event':
            real_event_type = event_data.get('event_type')
            if real_event_type == 'message.received':
                return process_message_received(event_data)
            # Silently acknowledge other event types
            return jsonify({'status': 'received', 'event_type': real_event_type}), 200
        
        # Format 2: Direct event type
        elif event_type == 'message.received':
            return process_message_received(event_data)
        
        # Format 3: Direct message field
        elif 'message' in event_data:
            return process_message_received(event_data)
        
        # Silently acknowledge any other events without warning
        return jsonify({'status': 'received', 'event_type': event_type}), 200
        
    except Exception as e:
        print(f"[ERROR] Webhook processing failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

def process_message_received(event_data):
    """Process received email message"""
    start_time = time.time()
    
    try:
        message = event_data.get('message', {})
        
        # Extract email information
        sender = message.get('from', '') or message.get('from_', '')
        subject = message.get('subject', '')
        body = message.get('text', '') or message.get('body', '')
        inbox_id = message.get('inbox_id', '')
        thread_id = message.get('thread_id', '')
        
        # Clean, professional logging output
        print("\n" + "=" * 60)
        print("EMAIL RECEIVED")
        print("-" * 60)
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Inbox: {inbox_id}")
        
        # Step 1: Classify email to determine specialized agent
        agent_type = classify_email(subject, body)
        
        # Step 2: Log agent assignment
        agent_names = {
            "billing": "BILLING_AGENT",
            "technical": "TECHNICAL_AGENT", 
            "general": "GENERAL_AGENT"
        }
        assigned_agent = agent_names.get(agent_type, "GENERAL_AGENT")
        
        print("-" * 60)
        print(f"AGENT CLASSIFICATION: {agent_type.upper()}")
        print(f"Assigned to: {assigned_agent}")
        
        sent = False
        if client and SEND_REAL:
            message_id = message.get('message_id', '')
            
            try:
                if inbox_id and message_id:
                    sender_addr = extract_email(sender)
                    
                    # Step 3: Generate AI response
                    print("-" * 60)
                    print("RESPONSE GENERATION")
                    print(f"Using OpenAI with specialized {agent_type} prompt...")
                    
                    ai_response = generate_ai_response(subject, body, sender, agent_type)
                    print(f"Generated response preview: {ai_response[:100]}...")
                    
                    # Step 4: Send reply via AgentMail
                    print("-" * 60)
                    print("SENDING REPLY")
                    
                    result = client.inboxes.messages.reply(
                        inbox_id=inbox_id,
                        message_id=message_id,
                        to=[sender_addr],
                        text=ai_response
                    )
                    
                    sent = True
                    processing_time = time.time() - start_time
                    
                    print(f"Status: SUCCESS")
                    print(f"Processing time: {processing_time:.2f}s")
                    print("=" * 60 + "\n")
                else:
                    print(f"[ERROR] Missing required parameters: inbox_id={inbox_id}, message_id={message_id}")
                    
            except Exception as e:
                print(f"[ERROR] Reply failed: {e}")
                import traceback
                traceback.print_exc()

        if not sent:
            print(f"[INFO] Simulated response to {sender}")
        
        return jsonify({
            'status': 'processed',
            'thread_id': thread_id,
            'classification': agent_type,
            'response_generated': True,
            'real_send': bool(sent)
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Message processing failed: {e}")
        return jsonify({'error': 'Message processing failed'}), 500

@app.route('/', methods=['GET'])
def status_page():
    """Status page"""
    return """
    <h1>🎯 AgentMail AI Auto-Reply Demo</h1>
    <p><strong>Status:</strong> Running</p>
    <p><strong>Function:</strong> Automatic email reception and reply</p>
    <p><strong>Supported Email Types:</strong></p>
    <ul>
        <li>Billing - Billing and payment issues</li>
        <li>Technical - Technical support and bug reports</li>
        <li>General - General inquiries</li>
    </ul>
    <p><a href="/health">Health Check</a></p>
    <p><a href="/admin/summary">📊 Admin Summary Dashboard</a></p>
    """, 200

@app.route('/admin/summary', methods=['GET'])
def admin_summary():
    """Admin dashboard with AI-powered insights"""
    import sys
    try:
        from datetime import datetime, timedelta, timezone
        
        # Initialize data structure
        summary_data = {
            "metrics": {
                "total_emails_sent": 0,
                "total_emails_received": 0,
                "time_range": "last 24 hours"
            },
            "recent_threads": [],
            "inbox_breakdown": {}
        }
        
        ai_summary = ""
        
        # Try to fetch data from AgentMail APIs
        if client:
            try:
                
                # Get metrics for last 24 hours (use UTC timezone for ISO format)
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=1)
                
                # Fetch metrics
                try:
                    metrics = client.metrics.list(
                        start_timestamp=start_time,
                        end_timestamp=end_time
                    )
                    
                    # Parse metrics response
                    if hasattr(metrics, 'message'):
                        # ListMetricsResponse object
                        sent_count = len(metrics.message.sent) if hasattr(metrics.message, 'sent') else 0
                        received_count = len(metrics.message.received) if hasattr(metrics.message, 'received') else 0
                        summary_data["metrics"]["total_emails_sent"] = sent_count
                        summary_data["metrics"]["total_emails_received"] = received_count
                    elif isinstance(metrics, dict):
                        summary_data["metrics"]["total_emails_sent"] = metrics.get("emails_sent", 0)
                        summary_data["metrics"]["total_emails_received"] = metrics.get("emails_received", 0)
                except Exception as e:
                    print(f"[WARN] Failed to fetch metrics: {e}")
                
                # Fetch all threads using the threads.list() API
                try:
                    threads_response = client.threads.list()
                    
                    thread_list = []
                    
                    # Handle ListThreadsResponse object
                    if hasattr(threads_response, 'threads'):
                        thread_list = threads_response.threads
                    elif isinstance(threads_response, list):
                        thread_list = threads_response
                    elif hasattr(threads_response, 'data'):
                        thread_list = threads_response.data
                    elif isinstance(threads_response, dict):
                        thread_list = threads_response.get('data', [])
                    
                    # Process each thread
                    for thread in thread_list[:50]:  # Limit to 50 most recent threads
                        thread_info = {}
                        
                        try:
                            # Handle ThreadItem objects from AgentMail SDK
                            if hasattr(thread, 'thread_id'):
                                # This is a ThreadItem object
                                senders = getattr(thread, "senders", [])
                                if isinstance(senders, list) and senders:
                                    sender_display = senders[0] if len(senders) == 1 else f"{senders[0]} +{len(senders)-1}"
                                else:
                                    sender_display = "Unknown"
                                
                                # Format timestamp
                                timestamp = getattr(thread, "updated_at", None) or getattr(thread, "created_at", None)
                                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "N/A"
                                
                                thread_info = {
                                    "thread_id": getattr(thread, "thread_id", "N/A"),
                                    "subject": getattr(thread, "subject", "No subject"),
                                    "from": sender_display,
                                    "inbox": getattr(thread, "inbox_id", "N/A"),
                                    "timestamp": timestamp_str
                                }
                            elif isinstance(thread, dict):
                                # Fallback for dict format
                                senders = thread.get("senders", [])
                                if isinstance(senders, list) and senders:
                                    sender_display = senders[0] if len(senders) == 1 else f"{senders[0]} +{len(senders)-1}"
                                else:
                                    sender_display = "Unknown"
                                
                                thread_info = {
                                    "thread_id": thread.get("id", thread.get("thread_id", "N/A")),
                                    "subject": thread.get("subject", "No subject"),
                                    "from": sender_display,
                                    "inbox": thread.get("inbox_id", "N/A"),
                                    "timestamp": str(thread.get("updated_at", thread.get("created_at", "N/A")))
                                }
                            
                            summary_data["recent_threads"].append(thread_info)
                            
                            # Update inbox breakdown
                            inbox_id = thread_info["inbox"]
                            if inbox_id and inbox_id != "N/A":
                                if inbox_id not in summary_data["inbox_breakdown"]:
                                    summary_data["inbox_breakdown"][inbox_id] = 0
                                summary_data["inbox_breakdown"][inbox_id] += 1
                        
                        except Exception as e:
                            print(f"[WARN] Failed to process thread: {e}")
                            continue
                            
                except Exception as e:
                    print(f"[WARN] Failed to fetch threads: {e}")
                    import traceback
                    traceback.print_exc()
                    
            except Exception as e:
                print(f"[ERROR] Failed to fetch AgentMail data: {e}")
        
        # Analyze threads for priority categorization
        priority_keywords = ["charged twice", "double charge", "refund", "error", "not working", "urgent", "complaint", "problem", "issue", "broken", "failed", "bug"]
        low_priority_keywords = ["champions league", "sports", "fun stuff", "football", "soccer", "game"]
        
        priority_issues = []
        routine_inquiries = []
        agent_stats = {"billing": 0, "technical": 0, "general": 0}
        
        for thread in summary_data['recent_threads']:
            subject_lower = thread['subject'].lower()
            thread_preview = f"{thread['subject']} (from {thread['from'].split()[0] if thread['from'] else 'Unknown'})"
            
            # Classify by agent type based on subject
            if any(kw in subject_lower for kw in ["bill", "billing", "payment", "charge", "refund", "invoice"]):
                agent_stats["billing"] += 1
                # Check if it's a priority issue
                if any(kw in subject_lower for kw in priority_keywords):
                    priority_issues.append({"thread_id": thread['thread_id'][:8], "subject": thread['subject'], "from": thread['from']})
                else:
                    routine_inquiries.append(thread_preview)
            elif any(kw in subject_lower for kw in ["error", "bug", "crash", "not working", "broken", "issue"]):
                agent_stats["technical"] += 1
                priority_issues.append({"thread_id": thread['thread_id'][:8], "subject": thread['subject'], "from": thread['from']})
            elif any(kw in subject_lower for kw in low_priority_keywords):
                agent_stats["general"] += 1
                routine_inquiries.append(thread_preview)
            else:
                agent_stats["general"] += 1
                routine_inquiries.append(thread_preview)
        
        # Generate AI summary if OpenAI is available
        if openai_available and openai_client:
            try:
                # Prepare priority examples
                priority_subjects = [f"{p['subject'][:50]}... (thread {p['thread_id']})" for p in priority_issues[:3]]
                routine_subjects = routine_inquiries[:3]
                
                prompt = f"""You are analyzing email activity for an admin dashboard. Provide a 2-3 sentence summary that:
- Highlights any HIGH PRIORITY issues that need admin attention (billing problems, errors, complaints)
- Mentions routine/low-priority traffic briefly
- Suggests action items if critical issues detected

Data:
- Total emails sent: {summary_data['metrics']['total_emails_sent']}
- Total emails received: {summary_data['metrics']['total_emails_received']}
- High priority issues: {len(priority_issues)} - Examples: {', '.join(priority_subjects) if priority_subjects else 'None'}
- Routine inquiries: {len(routine_inquiries)} - Examples: {', '.join(routine_subjects) if routine_subjects else 'None'}
- Agent breakdown: Billing={agent_stats['billing']}, Technical={agent_stats['technical']}, General={agent_stats['general']}
- Active inboxes: {len(summary_data['inbox_breakdown'])}

Format: Start with priority issues if any exist (use ⚠️ emoji), then overall stats. Be specific about issues requiring attention."""

                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an executive assistant providing concise, actionable email activity summaries. Always highlight critical issues first."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                
                ai_summary = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[WARN] Failed to generate AI summary: {e}")
                # Fallback to manual summary
                if priority_issues:
                    ai_summary = f"⚠️ ATTENTION NEEDED: {len(priority_issues)} high-priority issue(s) detected requiring review. Additionally, {len(routine_inquiries)} routine inquiries were processed automatically."
                else:
                    ai_summary = f"No critical issues detected. System processed {summary_data['metrics']['total_emails_received']} emails across {len(summary_data['inbox_breakdown'])} inboxes in the last 24 hours, primarily routine inquiries handled by automated agents."
        else:
            # Fallback when OpenAI is not available
            if priority_issues:
                ai_summary = f"⚠️ ATTENTION NEEDED: {len(priority_issues)} high-priority issue(s) detected requiring review. Additionally, {len(routine_inquiries)} routine inquiries were processed automatically."
            else:
                ai_summary = f"No critical issues detected. System processed {summary_data['metrics']['total_emails_received']} emails across {len(summary_data['inbox_breakdown'])} inboxes in the last 24 hours, primarily routine inquiries handled by automated agents."
        
        # Build HTML response
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Summary Dashboard</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 1200px;
                    margin: 40px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .summary-box {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 12px;
                    margin-bottom: 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }}
                .summary-box h2 {{
                    margin-top: 0;
                    font-size: 24px;
                }}
                .metrics {{
                    background: white;
                    padding: 25px;
                    border-radius: 8px;
                    margin-bottom: 25px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .metrics h3 {{
                    margin-top: 0;
                    color: #333;
                }}
                .metric-item {{
                    display: inline-block;
                    margin: 10px 20px 10px 0;
                    padding: 15px 25px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    border-left: 4px solid #667eea;
                }}
                .metric-label {{
                    font-size: 12px;
                    color: #666;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .metric-value {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #333;
                    margin-top: 5px;
                }}
                table {{
                    width: 100%;
                    background: white;
                    border-collapse: collapse;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                th {{
                    background: #667eea;
                    color: white;
                    padding: 15px;
                    text-align: left;
                    font-weight: 600;
                }}
                td {{
                    padding: 12px 15px;
                    border-bottom: 1px solid #eee;
                }}
                tr:hover {{
                    background: #f8f9fa;
                }}
                .inbox-list {{
                    background: white;
                    padding: 25px;
                    border-radius: 8px;
                    margin-top: 25px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .inbox-item {{
                    padding: 10px;
                    margin: 8px 0;
                    background: #f8f9fa;
                    border-radius: 4px;
                    display: flex;
                    justify-content: space-between;
                }}
                .back-link {{
                    display: inline-block;
                    margin-top: 20px;
                    color: #667eea;
                    text-decoration: none;
                    font-weight: 500;
                }}
                .back-link:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <h1>📊 Admin Summary Dashboard</h1>
            
            <div class="summary-box">
                <h2>🤖 AI Executive Summary</h2>
                <p>{ai_summary}</p>
            </div>
            
            <div class="metrics">
                <h3>📈 Email Metrics ({summary_data['metrics']['time_range']})</h3>
                <div class="metric-item">
                    <div class="metric-label">Emails Sent</div>
                    <div class="metric-value">{summary_data['metrics']['total_emails_sent']}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Emails Received</div>
                    <div class="metric-value">{summary_data['metrics']['total_emails_received']}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Active Inboxes</div>
                    <div class="metric-value">{len(summary_data['inbox_breakdown'])}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Total Threads</div>
                    <div class="metric-value">{len(summary_data['recent_threads'])}</div>
                </div>
            </div>
            
            <h3>📬 Recent Email Threads</h3>
            <table>
                <thead>
                    <tr>
                        <th>Thread ID</th>
                        <th>Subject</th>
                        <th>From</th>
                        <th>Inbox</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        if summary_data['recent_threads']:
            for thread in summary_data['recent_threads'][:20]:  # Show max 20
                html += f"""
                    <tr>
                        <td>{thread['thread_id'][:20]}...</td>
                        <td>{thread['subject']}</td>
                        <td>{thread['from']}</td>
                        <td>{thread['inbox'][:15]}...</td>
                        <td>{thread['timestamp']}</td>
                    </tr>
                """
        else:
            html += """
                    <tr>
                        <td colspan="5" style="text-align: center; color: #999;">No threads available</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
            
            <div class="inbox-list">
                <h3>📥 Inbox Breakdown</h3>
        """
        
        if summary_data['inbox_breakdown']:
            for inbox_id, count in summary_data['inbox_breakdown'].items():
                html += f"""
                <div class="inbox-item">
                    <span>{inbox_id}</span>
                    <strong>{count} threads</strong>
                </div>
                """
        else:
            html += "<p style='color: #999;'>No inbox data available</p>"
        
        html += """
            </div>
            
            <a href="/" class="back-link">← Back to Home</a>
        </body>
        </html>
        """
        
        return html, 200
        
    except Exception as e:
        print(f"[ERROR] Admin summary failed: {e}")
        import traceback
        traceback.print_exc()
        return f"""
        <html>
        <body>
            <h1>Error</h1>
            <p>Failed to generate admin summary: {str(e)}</p>
            <a href="/">Back to Home</a>
        </body>
        </html>
        """, 500

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("STARTING AGENTMAIL AI AUTO-REPLY SERVICE")
    print("=" * 60)
    print(f"[INFO] Webhook URL: https://chemigraphically-unmatched-jay.ngrok-free.dev/webhook/agentmail")
    print(f"[INFO] Server listening on port 5000")
    print("[INFO] Ready to process incoming emails...")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
