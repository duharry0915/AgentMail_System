"""
Configuration management for distributed AgentMail system
Handles environment variables, logging, and system constants
"""

import os
import logging
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """System configuration with distributed system parameters"""
    
    # AgentMail API Configuration
    AGENTMAIL_API_KEY: str = os.getenv("AGENTMAIL_API_KEY", "")
    
    # Distributed System Configuration
    NODE_ID: str = os.getenv("NODE_ID", f"agent-{os.getpid()}")
    CLUSTER_NODES: List[str] = os.getenv("CLUSTER_NODES", "localhost:5000").split(",")
    
    # Paxos Configuration
    PAXOS_MAJORITY_SIZE: int = len(CLUSTER_NODES) // 2 + 1
    PAXOS_TIMEOUT: float = float(os.getenv("PAXOS_TIMEOUT", "5.0"))
    PAXOS_RETRY_INTERVAL: float = float(os.getenv("PAXOS_RETRY_INTERVAL", "1.0"))
    
    # Health Monitoring
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "10"))
    FAILURE_THRESHOLD: int = int(os.getenv("FAILURE_THRESHOLD", "3"))
    RECOVERY_TIMEOUT: int = int(os.getenv("RECOVERY_TIMEOUT", "30"))
    
    # Load Balancing
    AGENT_SPECIALIZATIONS: Dict[str, List[str]] = {
        "support": ["customer", "billing", "technical"],
        "sales": ["pricing", "demo", "enterprise"],
        "general": ["info", "routing", "fallback"]
    }
    
    # Conversation State Management
    STATE_REPLICATION_FACTOR: int = int(os.getenv("STATE_REPLICATION_FACTOR", "3"))
    STATE_SYNC_INTERVAL: int = int(os.getenv("STATE_SYNC_INTERVAL", "5"))
    
    # Flask Configuration
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # Monitoring
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.AGENTMAIL_API_KEY:
            raise ValueError("AGENTMAIL_API_KEY is required")
        
        if len(cls.CLUSTER_NODES) < 3:
            logging.warning("Cluster size < 3, Paxos may not work optimally")
        
        return True

def setup_logging():
    """Configure distributed system logging"""
    log_format = (
        f"[{Config.NODE_ID}] %(asctime)s - %(name)s - %(levelname)s - "
        f"%(filename)s:%(lineno)d - %(message)s"
    )
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"logs/{Config.NODE_ID}.log", mode='a')
        ]
    )
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    return logging.getLogger(__name__)

# Initialize logging
logger = setup_logging()

# Validate configuration on import
try:
    Config.validate()
    logger.info(f"Configuration validated for node {Config.NODE_ID}")
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    sys.exit(1)
