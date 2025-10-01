"""
Monitoring and Analytics System
Provides real-time monitoring, metrics collection, and system analytics
"""

import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import asyncio

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System-wide metrics snapshot"""
    timestamp: float
    active_agents: int
    total_conversations: int
    messages_processed: int
    consensus_operations: int
    average_response_time: float
    system_health: str
    node_id: str = Config.NODE_ID

@dataclass
class AgentMetrics:
    """Individual agent metrics"""
    agent_id: str
    status: str
    load: int
    specializations: List[str]
    messages_handled: int
    average_processing_time: float
    last_activity: float
    error_rate: float

class MetricsCollector:
    """Collects and aggregates system metrics"""
    
    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 snapshots
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.processing_times: deque = deque(maxlen=100)
        self.error_counts: defaultdict = defaultdict(int)
        self.lock = threading.RLock()
        
        # Prometheus metrics
        self.setup_prometheus_metrics()
        
    def setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # System metrics
        try:
            self.system_health_gauge = Gauge('system_health_status', 'System health status (1=healthy, 0=unhealthy)')
        except ValueError:
            # Metric already exists, get existing one
            from prometheus_client import REGISTRY
            self.system_health_gauge = REGISTRY._names_to_collectors.get('system_health_status')
        
        try:
            self.active_agents_gauge = Gauge('active_agents_total', 'Number of active agents')
        except ValueError:
            from prometheus_client import REGISTRY
            self.active_agents_gauge = REGISTRY._names_to_collectors.get('active_agents_total')
            
        try:
            self.total_conversations_gauge = Gauge('conversations_total', 'Total active conversations')
        except ValueError:
            from prometheus_client import REGISTRY
            self.total_conversations_gauge = REGISTRY._names_to_collectors.get('conversations_total')
        
        # Performance metrics
        try:
            self.message_processing_time = Histogram(
                'message_processing_duration_seconds',
                'Time spent processing messages',
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
            )
        except ValueError:
            from prometheus_client import REGISTRY
            self.message_processing_time = REGISTRY._names_to_collectors.get('message_processing_duration_seconds')
            
        try:
            self.consensus_duration = Histogram(
                'consensus_operation_duration_seconds',
                'Time spent on consensus operations',
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
            )
        except ValueError:
            from prometheus_client import REGISTRY
            self.consensus_duration = REGISTRY._names_to_collectors.get('consensus_operation_duration_seconds')
        
        # Error metrics
        try:
            self.error_counter = Counter('errors_total', 'Total errors', ['error_type', 'component'])
        except ValueError:
            from prometheus_client import REGISTRY
            self.error_counter = REGISTRY._names_to_collectors.get('errors_total')
            
        try:
            self.failed_consensus_counter = Counter('failed_consensus_total', 'Failed consensus operations')
        except ValueError:
            from prometheus_client import REGISTRY
            self.failed_consensus_counter = REGISTRY._names_to_collectors.get('failed_consensus_total')
        
        # Agent metrics
        try:
            self.agent_load_gauge = Gauge('agent_load', 'Current agent load', ['agent_id'])
        except ValueError:
            from prometheus_client import REGISTRY
            self.agent_load_gauge = REGISTRY._names_to_collectors.get('agent_load')
            
        try:
            self.agent_status_info = Info('agent_status', 'Agent status information')
        except ValueError:
            from prometheus_client import REGISTRY
            self.agent_status_info = REGISTRY._names_to_collectors.get('agent_status')
        
        # Business metrics
        try:
            self.auto_responses_counter = Counter('auto_responses_total', 'Auto responses sent', ['type'])
        except ValueError:
            from prometheus_client import REGISTRY
            self.auto_responses_counter = REGISTRY._names_to_collectors.get('auto_responses_total')
            
        try:
            self.escalations_counter = Counter('escalations_total', 'Messages escalated to humans', ['reason'])
        except ValueError:
            from prometheus_client import REGISTRY
            self.escalations_counter = REGISTRY._names_to_collectors.get('escalations_total')
        
    def record_message_processing(self, processing_time: float, success: bool = True):
        """Record message processing metrics"""
        with self.lock:
            self.message_processing_time.observe(processing_time)
            self.processing_times.append(processing_time)
            
            if not success:
                self.error_counter.labels(error_type='processing', component='email_processor').inc()
    
    def record_consensus_operation(self, duration: float, success: bool = True):
        """Record consensus operation metrics"""
        with self.lock:
            self.consensus_duration.observe(duration)
            
            if not success:
                self.failed_consensus_counter.inc()
    
    def record_agent_metrics(self, agent_id: str, metrics: AgentMetrics):
        """Record metrics for a specific agent"""
        with self.lock:
            self.agent_metrics[agent_id] = metrics
            self.agent_load_gauge.labels(agent_id=agent_id).set(metrics.load)
    
    def record_auto_response(self, response_type: str):
        """Record auto response sent"""
        self.auto_responses_counter.labels(type=response_type).inc()
    
    def record_escalation(self, reason: str):
        """Record message escalation"""
        self.escalations_counter.labels(reason=reason).inc()
    
    def record_error(self, error_type: str, component: str):
        """Record system error"""
        self.error_counter.labels(error_type=error_type, component=component).inc()
        with self.lock:
            self.error_counts[f"{component}:{error_type}"] += 1
    
    def get_system_snapshot(self) -> SystemMetrics:
        """Get current system metrics snapshot"""
        with self.lock:
            avg_response_time = (
                sum(self.processing_times) / len(self.processing_times)
                if self.processing_times else 0.0
            )
            
            # Determine system health
            recent_errors = sum(
                count for key, count in self.error_counts.items()
                if time.time() - 300 < count  # Errors in last 5 minutes
            )
            system_health = "healthy" if recent_errors < 10 else "degraded" if recent_errors < 50 else "unhealthy"
            
            snapshot = SystemMetrics(
                timestamp=time.time(),
                active_agents=len([m for m in self.agent_metrics.values() if m.status == "healthy"]),
                total_conversations=0,  # Would be populated from coordinator
                messages_processed=len(self.processing_times),
                consensus_operations=0,  # Would be tracked separately
                average_response_time=avg_response_time,
                system_health=system_health
            )
            
            self.metrics_history.append(snapshot)
            
            # Update Prometheus gauges
            self.system_health_gauge.set(1 if system_health == "healthy" else 0)
            self.active_agents_gauge.set(snapshot.active_agents)
            
            return snapshot
    
    def get_metrics_history(self, duration_seconds: int = 3600) -> List[SystemMetrics]:
        """Get metrics history for specified duration"""
        cutoff_time = time.time() - duration_seconds
        with self.lock:
            return [
                snapshot for snapshot in self.metrics_history
                if snapshot.timestamp >= cutoff_time
            ]
    
    def get_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get current agent metrics"""
        with self.lock:
            return dict(self.agent_metrics)

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.health_checks = {}
        self.running = False
        
    def register_health_check(self, name: str, check_func, interval: int = 30):
        """Register a health check function"""
        self.health_checks[name] = {
            'func': check_func,
            'interval': interval,
            'last_run': 0,
            'status': 'unknown',
            'message': ''
        }
    
    async def start_monitoring(self):
        """Start health monitoring loop"""
        self.running = True
        
        while self.running:
            await self._run_health_checks()
            await asyncio.sleep(10)  # Run every 10 seconds
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.running = False
    
    async def _run_health_checks(self):
        """Run all registered health checks"""
        current_time = time.time()
        
        for name, check_info in self.health_checks.items():
            if current_time - check_info['last_run'] >= check_info['interval']:
                try:
                    result = await self._run_single_check(check_info['func'])
                    check_info['status'] = 'healthy' if result['healthy'] else 'unhealthy'
                    check_info['message'] = result.get('message', '')
                    check_info['last_run'] = current_time
                    
                    if not result['healthy']:
                        self.metrics_collector.record_error('health_check', name)
                        logger.warning(f"Health check failed: {name} - {result.get('message', '')}")
                        
                except Exception as e:
                    check_info['status'] = 'error'
                    check_info['message'] = str(e)
                    check_info['last_run'] = current_time
                    self.metrics_collector.record_error('health_check_error', name)
                    logger.error(f"Health check error: {name} - {e}")
    
    async def _run_single_check(self, check_func) -> Dict[str, Any]:
        """Run a single health check"""
        if asyncio.iscoroutinefunction(check_func):
            return await check_func()
        else:
            return check_func()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        overall_healthy = all(
            check['status'] == 'healthy' 
            for check in self.health_checks.values()
        )
        
        return {
            'overall_healthy': overall_healthy,
            'checks': dict(self.health_checks),
            'timestamp': time.time()
        }

class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules = []
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        
    def add_alert_rule(self, name: str, condition_func, severity: str = 'warning', 
                      cooldown: int = 300):
        """Add an alert rule"""
        self.alert_rules.append({
            'name': name,
            'condition': condition_func,
            'severity': severity,
            'cooldown': cooldown,
            'last_triggered': 0
        })
    
    async def check_alerts(self):
        """Check all alert conditions"""
        current_time = time.time()
        snapshot = self.metrics_collector.get_system_snapshot()
        
        for rule in self.alert_rules:
            try:
                # Check if cooldown period has passed
                if current_time - rule['last_triggered'] < rule['cooldown']:
                    continue
                
                # Evaluate condition
                if rule['condition'](snapshot):
                    await self._trigger_alert(rule, snapshot)
                    rule['last_triggered'] = current_time
                    
            except Exception as e:
                logger.error(f"Alert rule evaluation error: {rule['name']} - {e}")
    
    async def _trigger_alert(self, rule: Dict[str, Any], snapshot: SystemMetrics):
        """Trigger an alert"""
        alert = {
            'name': rule['name'],
            'severity': rule['severity'],
            'message': f"Alert triggered: {rule['name']}",
            'timestamp': time.time(),
            'snapshot': asdict(snapshot)
        }
        
        self.active_alerts[rule['name']] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"ALERT: {alert['message']} (severity: {alert['severity']})")
        
        # In a real system, this would send notifications
        # (email, Slack, PagerDuty, etc.)
    
    def resolve_alert(self, alert_name: str):
        """Resolve an active alert"""
        if alert_name in self.active_alerts:
            del self.active_alerts[alert_name]
            logger.info(f"Alert resolved: {alert_name}")
    
    def get_active_alerts(self) -> Dict[str, Any]:
        """Get currently active alerts"""
        return dict(self.active_alerts)

class MonitoringSystem:
    """Main monitoring system coordinator"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker(self.metrics_collector)
        self.alert_manager = AlertManager(self.metrics_collector)
        self.running = False
        
        self._setup_default_health_checks()
        self._setup_default_alerts()
    
    def _setup_default_health_checks(self):
        """Setup default health checks"""
        
        async def check_agentmail_api():
            """Check AgentMail API connectivity"""
            try:
                from agentmail import AgentMail
                client = AgentMail(api_key=Config.AGENTMAIL_API_KEY)
                # Simple API call to check connectivity
                inboxes = client.inboxes.list()
                return {'healthy': True, 'message': f'API accessible, {len(inboxes)} inboxes'}
            except Exception as e:
                return {'healthy': False, 'message': f'API error: {str(e)}'}
        
        def check_memory_usage():
            """Check system memory usage"""
            try:
                import psutil
                memory = psutil.virtual_memory()
                usage_percent = memory.percent
                return {
                    'healthy': usage_percent < 90,
                    'message': f'Memory usage: {usage_percent:.1f}%'
                }
            except ImportError:
                return {'healthy': True, 'message': 'psutil not available'}
        
        def check_disk_space():
            """Check disk space"""
            try:
                import psutil
                disk = psutil.disk_usage('/')
                usage_percent = (disk.used / disk.total) * 100
                return {
                    'healthy': usage_percent < 85,
                    'message': f'Disk usage: {usage_percent:.1f}%'
                }
            except ImportError:
                return {'healthy': True, 'message': 'psutil not available'}
        
        self.health_checker.register_health_check('agentmail_api', check_agentmail_api, 60)
        self.health_checker.register_health_check('memory_usage', check_memory_usage, 30)
        self.health_checker.register_health_check('disk_space', check_disk_space, 60)
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        
        # High error rate alert
        self.alert_manager.add_alert_rule(
            'high_error_rate',
            lambda snapshot: len(self.metrics_collector.error_counts) > 10,
            'critical',
            300
        )
        
        # System unhealthy alert
        self.alert_manager.add_alert_rule(
            'system_unhealthy',
            lambda snapshot: snapshot.system_health == 'unhealthy',
            'critical',
            600
        )
        
        # No active agents alert
        self.alert_manager.add_alert_rule(
            'no_active_agents',
            lambda snapshot: snapshot.active_agents == 0,
            'critical',
            300
        )
        
        # High response time alert
        self.alert_manager.add_alert_rule(
            'high_response_time',
            lambda snapshot: snapshot.average_response_time > 10.0,
            'warning',
            600
        )
    
    async def start(self):
        """Start monitoring system"""
        self.running = True
        
        # Start Prometheus metrics server
        start_http_server(Config.METRICS_PORT)
        logger.info(f"Prometheus metrics server started on port {Config.METRICS_PORT}")
        
        # Start monitoring tasks
        asyncio.create_task(self.health_checker.start_monitoring())
        asyncio.create_task(self._alert_monitoring_loop())
        asyncio.create_task(self._metrics_collection_loop())
        
        logger.info("Monitoring system started")
    
    async def stop(self):
        """Stop monitoring system"""
        self.running = False
        self.health_checker.stop_monitoring()
        logger.info("Monitoring system stopped")
    
    async def _alert_monitoring_loop(self):
        """Alert monitoring loop"""
        while self.running:
            await self.alert_manager.check_alerts()
            await asyncio.sleep(30)  # Check alerts every 30 seconds
    
    async def _metrics_collection_loop(self):
        """Metrics collection loop"""
        while self.running:
            self.metrics_collector.get_system_snapshot()
            await asyncio.sleep(60)  # Collect metrics every minute
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        return {
            'system_metrics': asdict(self.metrics_collector.get_system_snapshot()),
            'agent_metrics': {
                agent_id: asdict(metrics) 
                for agent_id, metrics in self.metrics_collector.get_agent_metrics().items()
            },
            'health_status': self.health_checker.get_health_status(),
            'active_alerts': self.alert_manager.get_active_alerts(),
            'metrics_history': [
                asdict(snapshot) 
                for snapshot in self.metrics_collector.get_metrics_history(3600)
            ]
        }

# Global monitoring instance
monitoring_system = MonitoringSystem()
