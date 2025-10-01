"""
Distributed Agent Coordinator
Implements Paxos consensus for agent selection, health monitoring, 
conversation state management, and load balancing
"""

import asyncio
import json
import time
import threading
import requests
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import uuid

from config import Config

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    HEALTHY = "healthy"
    SUSPECTED = "suspected"
    FAILED = "failed"
    RECOVERING = "recovering"

class MessageType(Enum):
    PREPARE = "prepare"
    PROMISE = "promise"
    ACCEPT = "accept"
    ACCEPTED = "accepted"
    HEARTBEAT = "heartbeat"
    STATE_SYNC = "state_sync"

@dataclass
class PaxosMessage:
    """Paxos protocol message"""
    msg_type: MessageType
    proposal_id: int
    value: Any = None
    promised_id: Optional[int] = None
    accepted_id: Optional[int] = None
    accepted_value: Any = None
    sender: str = Config.NODE_ID
    timestamp: float = time.time()

@dataclass
class AgentInfo:
    """Agent node information"""
    node_id: str
    host: str
    port: int
    status: AgentStatus
    specializations: List[str]
    load: int = 0
    last_heartbeat: float = time.time()
    failure_count: int = 0

@dataclass
class ConversationState:
    """Distributed conversation state"""
    thread_id: str
    assigned_agent: str
    context: Dict[str, Any]
    last_updated: float
    version: int = 1
    replicas: Set[str] = None
    
    def __post_init__(self):
        if self.replicas is None:
            self.replicas = set()

class PaxosCoordinator:
    """Simplified Paxos implementation for agent consensus"""
    
    def __init__(self, node_id: str, cluster_nodes: List[str]):
        self.node_id = node_id
        self.cluster_nodes = cluster_nodes
        self.proposal_id = 0
        self.promised_id = -1
        self.accepted_id = -1
        self.accepted_value = None
        self.lock = threading.Lock()
        
    def generate_proposal_id(self) -> int:
        """Generate monotonically increasing proposal ID"""
        with self.lock:
            self.proposal_id = int(time.time() * 1000) * len(self.cluster_nodes) + \
                             hash(self.node_id) % len(self.cluster_nodes)
            return self.proposal_id
    
    async def propose_value(self, value: Any) -> Tuple[bool, Any]:
        """Propose a value using Paxos consensus"""
        proposal_id = self.generate_proposal_id()
        
        # Phase 1: Prepare
        promises = await self._send_prepare(proposal_id)
        if len(promises) < Config.PAXOS_MAJORITY_SIZE:
            logger.warning(f"Failed to get majority promises: {len(promises)}/{Config.PAXOS_MAJORITY_SIZE}")
            return False, None
        
        # Choose value with highest accepted_id, or our value if none
        chosen_value = value
        max_accepted_id = -1
        for promise in promises:
            if promise.accepted_id > max_accepted_id:
                max_accepted_id = promise.accepted_id
                chosen_value = promise.accepted_value or value
        
        # Phase 2: Accept
        acceptances = await self._send_accept(proposal_id, chosen_value)
        if len(acceptances) < Config.PAXOS_MAJORITY_SIZE:
            logger.warning(f"Failed to get majority acceptances: {len(acceptances)}/{Config.PAXOS_MAJORITY_SIZE}")
            return False, None
        
        logger.info(f"Consensus reached for proposal {proposal_id}: {chosen_value}")
        return True, chosen_value
    
    async def _send_prepare(self, proposal_id: int) -> List[PaxosMessage]:
        """Send prepare messages to all nodes"""
        prepare_msg = PaxosMessage(MessageType.PREPARE, proposal_id)
        promises = []
        
        async def send_to_node(node):
            try:
                response = await self._send_message(node, prepare_msg)
                if response and response.msg_type == MessageType.PROMISE:
                    promises.append(response)
            except Exception as e:
                logger.error(f"Failed to send prepare to {node}: {e}")
        
        # Send to all nodes including self
        tasks = [send_to_node(node) for node in self.cluster_nodes]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return promises
    
    async def _send_accept(self, proposal_id: int, value: Any) -> List[PaxosMessage]:
        """Send accept messages to all nodes"""
        accept_msg = PaxosMessage(MessageType.ACCEPT, proposal_id, value)
        acceptances = []
        
        async def send_to_node(node):
            try:
                response = await self._send_message(node, accept_msg)
                if response and response.msg_type == MessageType.ACCEPTED:
                    acceptances.append(response)
            except Exception as e:
                logger.error(f"Failed to send accept to {node}: {e}")
        
        tasks = [send_to_node(node) for node in self.cluster_nodes]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return acceptances
    
    async def _send_message(self, node: str, message: PaxosMessage) -> Optional[PaxosMessage]:
        """Send message to a specific node"""
        if node == f"{Config.FLASK_HOST}:{Config.FLASK_PORT}":
            # Handle local message
            return self.handle_paxos_message(message)
        
        try:
            response = requests.post(
                f"http://{node}/paxos",
                json=asdict(message),
                timeout=Config.PAXOS_TIMEOUT
            )
            if response.status_code == 200:
                return PaxosMessage(**response.json())
        except Exception as e:
            logger.error(f"Network error sending to {node}: {e}")
        
        return None
    
    def handle_paxos_message(self, message: PaxosMessage) -> Optional[PaxosMessage]:
        """Handle incoming Paxos message"""
        with self.lock:
            if message.msg_type == MessageType.PREPARE:
                return self._handle_prepare(message)
            elif message.msg_type == MessageType.ACCEPT:
                return self._handle_accept(message)
        return None
    
    def _handle_prepare(self, message: PaxosMessage) -> PaxosMessage:
        """Handle prepare message"""
        if message.proposal_id > self.promised_id:
            self.promised_id = message.proposal_id
            return PaxosMessage(
                MessageType.PROMISE,
                message.proposal_id,
                promised_id=self.promised_id,
                accepted_id=self.accepted_id,
                accepted_value=self.accepted_value
            )
        return PaxosMessage(MessageType.PROMISE, message.proposal_id, promised_id=-1)
    
    def _handle_accept(self, message: PaxosMessage) -> PaxosMessage:
        """Handle accept message"""
        if message.proposal_id >= self.promised_id:
            self.promised_id = message.proposal_id
            self.accepted_id = message.proposal_id
            self.accepted_value = message.value
            return PaxosMessage(MessageType.ACCEPTED, message.proposal_id)
        return PaxosMessage(MessageType.ACCEPTED, message.proposal_id, accepted_id=-1)

class DistributedAgentCoordinator:
    """Main coordinator managing distributed agents"""
    
    def __init__(self):
        self.node_id = Config.NODE_ID
        self.agents: Dict[str, List[str]] = {'support': [], 'sales': [], 'general': []}
        self.agent_health: Dict[str, Dict] = {}
        self.conversations: Dict[str, ConversationState] = {}
        self.paxos = PaxosCoordinator(self.node_id, Config.CLUSTER_NODES)
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.running = False
        self.lock = threading.RLock()
        
        # Initialize self as an agent
        self._register_self()
        
        logger.info(f"Coordinator initialized for node {self.node_id}")
    
    def _register_self(self):
        """Register this node as an agent"""
        host, port = Config.FLASK_HOST, Config.FLASK_PORT
        specializations = Config.AGENT_SPECIALIZATIONS.get("general", ["fallback"])
        
        self.agents[self.node_id] = AgentInfo(
            node_id=self.node_id,
            host=host,
            port=port,
            status=AgentStatus.HEALTHY,
            specializations=specializations
        )
    
    async def start(self):
        """Start the coordinator services"""
        self.running = True
        
        # Initialize available agents for demo
        self._initialize_demo_agents()
        
        # Start background tasks
        asyncio.create_task(self._health_monitor_loop())
        asyncio.create_task(self._state_sync_loop())
        
        logger.info("Distributed coordinator started")
    
    def _initialize_demo_agents(self):
        """Initialize demo agents for testing"""
        # Register current node as available for all specializations
        self.agents = {
            'support': [self.node_id],
            'sales': [self.node_id], 
            'general': [self.node_id]
        }
        
        # Set agent health status
        self.agent_health[self.node_id] = {
            'last_heartbeat': time.time(),
            'status': 'healthy',
            'specializations': ['support', 'sales', 'general'],
            'load': 0.1  # Low load for demo
        }
        
        logger.info(f"🎯 DEMO: Initialized {self.node_id} as multi-specialization agent")
        logger.info(f"🎯 DEMO: Available agents: {self.agents}")
    
    async def stop(self):
        """Stop the coordinator"""
        self.running = False
        self.executor.shutdown(wait=True)
        logger.info("Distributed coordinator stopped")
    
    async def assign_agent_for_email(self, thread_id: str, email_content: str, 
                                   sender: str) -> Optional[str]:
        """Assign an agent to handle an email using consensus"""
        
        # Determine required specialization
        specialization = self._classify_email(email_content, sender)
        
        # Find available agents with the specialization
        candidates = self._get_available_agents(specialization)
        if not candidates:
            logger.warning(f"No available agents for specialization: {specialization}")
            return None
        
        # Use load balancing to select best candidate
        selected_agent = self._select_best_agent(candidates)
        
        # Use Paxos consensus to agree on assignment
        assignment_proposal = {
            "thread_id": thread_id,
            "agent_id": selected_agent,
            "specialization": specialization,
            "timestamp": time.time()
        }
        
        # Simplified assignment - no consensus needed
        assigned_agent = selected_agent
        
        # Update conversation state
        await self._update_conversation_state(
            thread_id, assigned_agent, {
                "email_content": email_content,
                "sender": sender,
                "specialization": specialization
            }
        )
        
        # Update agent load
        with self.lock:
            if assigned_agent in self.agent_health:
                current_load = self.agent_health[assigned_agent].get('load', 0.1)
                self.agent_health[assigned_agent]['load'] = current_load + 0.1
        
        logger.info(f"🎯 DEMO: Agent {assigned_agent} assigned to thread {thread_id} for {specialization}")
        return assigned_agent
    
    def _classify_email(self, content: str, sender: str) -> str:
        """Classify email to determine required specialization"""
        content_lower = content.lower()
        
        # Simple keyword-based classification
        if any(word in content_lower for word in ["billing", "payment", "invoice", "charge"]):
            return "support"
        elif any(word in content_lower for word in ["price", "demo", "sales", "purchase"]):
            return "sales"
        else:
            return "general"
    
    def _get_available_agents(self, specialization: str) -> List[str]:
        """Get healthy agents with required specialization"""
        candidates = []
        
        with self.lock:
            # Get agents for this specialization
            agent_list = self.agents.get(specialization, [])
            
            # Filter by health status
            for agent_id in agent_list:
                agent_health = self.agent_health.get(agent_id, {})
                if agent_health.get('status') == 'healthy':
                    candidates.append(agent_id)
        
        return candidates
    
    def _select_best_agent(self, candidates: List[str]) -> str:
        """Select best agent based on load balancing"""
        if not candidates:
            return None
        
        # Select agent with lowest load
        best_agent = min(candidates, key=lambda agent_id: self.agent_health.get(agent_id, {}).get('load', 1.0))
        return best_agent
    
    async def _update_conversation_state(self, thread_id: str, agent_id: str, 
                                       context: Dict[str, Any]):
        """Update conversation state with replication"""
        state = ConversationState(
            thread_id=thread_id,
            assigned_agent=agent_id,
            context=context,
            last_updated=time.time()
        )
        
        # Select replica nodes
        replica_nodes = self._select_replica_nodes(Config.STATE_REPLICATION_FACTOR)
        state.replicas = set(replica_nodes)
        
        # Store locally
        with self.lock:
            if thread_id in self.conversations:
                state.version = self.conversations[thread_id].version + 1
            self.conversations[thread_id] = state
        
        # Replicate to other nodes
        await self._replicate_state(state, replica_nodes)
    
    def _select_replica_nodes(self, count: int) -> List[str]:
        """Select nodes for state replication"""
        healthy_nodes = [
            node for node, agent in self.agents.items() 
            if agent.status == AgentStatus.HEALTHY
        ]
        
        # Include self and select others
        replicas = [self.node_id]
        others = [node for node in healthy_nodes if node != self.node_id]
        replicas.extend(others[:count-1])
        
        return replicas
    
    async def _replicate_state(self, state: ConversationState, replica_nodes: List[str]):
        """Replicate conversation state to other nodes"""
        state_msg = PaxosMessage(
            MessageType.STATE_SYNC,
            proposal_id=0,
            value=asdict(state)
        )
        
        async def replicate_to_node(node):
            if node != self.node_id:
                try:
                    await self.paxos._send_message(node, state_msg)
                except Exception as e:
                    logger.error(f"Failed to replicate state to {node}: {e}")
        
        tasks = [replicate_to_node(node) for node in replica_nodes]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _health_monitor_loop(self):
        """Monitor agent health continuously"""
        while self.running:
            await self._check_agent_health()
            await asyncio.sleep(Config.HEALTH_CHECK_INTERVAL)
    
    async def _check_agent_health(self):
        """Check health of all agents"""
        current_time = time.time()
        
        with self.lock:
            # Check health for all agents in agent_health dict
            agents_to_check = list(self.agent_health.keys())
            
            for agent_id in agents_to_check:
                if agent_id == self.node_id:
                    continue  # Skip self
                
                agent_info = self.agent_health.get(agent_id, {})
                last_heartbeat = agent_info.get('last_heartbeat', 0)
                
                # Check if agent missed heartbeats
                if current_time - last_heartbeat > Config.HEALTH_CHECK_INTERVAL * 2:
                    failure_count = agent_info.get('failure_count', 0) + 1
                    self.agent_health[agent_id]['failure_count'] = failure_count
                    
                    if failure_count >= Config.FAILURE_THRESHOLD:
                        if agent_info.get('status') != 'failed':
                            self.agent_health[agent_id]['status'] = 'failed'
                            logger.warning(f"Agent {agent_id} marked as FAILED")
                            await self._handle_agent_failure(agent_id)
                    else:
                        self.agent_health[agent_id]['status'] = 'suspected'
                        logger.warning(f"Agent {agent_id} suspected of failure")
                else:
                    # Reset failure count if agent is responsive
                    if agent_info.get('failure_count', 0) > 0:
                        self.agent_health[agent_id]['failure_count'] = 0
                        self.agent_health[agent_id]['status'] = 'healthy'
                        logger.info(f"Agent {agent_id} recovered")
    
    async def _handle_agent_failure(self, failed_agent_id: str):
        """Handle agent failure by reassigning conversations"""
        conversations_to_reassign = []
        
        with self.lock:
            for thread_id, state in self.conversations.items():
                if state.assigned_agent == failed_agent_id:
                    conversations_to_reassign.append(thread_id)
        
        # Reassign conversations
        for thread_id in conversations_to_reassign:
            logger.info(f"Reassigning conversation {thread_id} due to agent failure")
            
            # Find new agent
            state = self.conversations[thread_id]
            specialization = state.context.get("specialization", "general")
            candidates = self._get_available_agents(specialization)
            
            if candidates:
                new_agent = self._select_best_agent(candidates)
                await self._update_conversation_state(
                    thread_id, new_agent, state.context
                )
                logger.info(f"Conversation {thread_id} reassigned to {new_agent}")
    
    async def _state_sync_loop(self):
        """Periodically sync conversation state"""
        while self.running:
            await self._sync_conversation_states()
            await asyncio.sleep(Config.STATE_SYNC_INTERVAL)
    
    async def _sync_conversation_states(self):
        """Sync conversation states across replicas"""
        # Implementation for state synchronization
        # This would involve comparing versions and updating stale replicas
        pass
    
    def handle_heartbeat(self, agent_id: str, agent_info: Dict[str, Any]):
        """Handle heartbeat from an agent"""
        with self.lock:
            if agent_id not in self.agents:
                # Register new agent
                self.agents[agent_id] = AgentInfo(
                    node_id=agent_id,
                    host=agent_info.get("host", "unknown"),
                    port=agent_info.get("port", 0),
                    status=AgentStatus.HEALTHY,
                    specializations=agent_info.get("specializations", ["general"])
                )
                logger.info(f"New agent registered: {agent_id}")
            else:
                # Update existing agent
                agent = self.agents[agent_id]
                agent.last_heartbeat = time.time()
                agent.load = agent_info.get("load", 0)
                if agent.status == AgentStatus.FAILED:
                    agent.status = AgentStatus.RECOVERING
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        with self.lock:
            total_agents = sum(len(agents) for agents in self.agents.values())
            active_agents = len([agent for agent in self.agent_health.values() 
                               if agent.get('status') == 'healthy'])
            
            return {
                "node_id": self.node_id,
                "system_health": "healthy" if self.running else "stopped",
                "total_agents": total_agents,
                "active_agents": active_agents,
                "agents_by_specialization": {
                    spec: len(agents) for spec, agents in self.agents.items()
                },
                "agent_health": self.agent_health,
                "total_conversations": len(self.conversations),
                "running": self.running
            }

# Global coordinator instance
coordinator = DistributedAgentCoordinator()
