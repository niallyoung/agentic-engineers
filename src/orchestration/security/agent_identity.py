"""
Agent Identity Verification — Prevent spoofing in DELEGATE/HANDBACK delegation chains.

Each agent generates a unique identity and signs all messages with their private key.
Identity chains are verified to ensure no spoofing in delegation relationships.
"""

import json
import hashlib
import logging
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)


class AgentIdentity:
    """
    Unique identity for an agent to prevent spoofing in delegation chains.
    
    Each agent:
    1. Generates a unique agent_id (UUID)
    2. Has RSA keypair for signing messages
    3. Maintains identity in all DELEGATE/HANDBACK messages
    4. Verifies downstream agents are who they claim to be
    """
    
    def __init__(self, agent_name: str, key_dir: Optional[Path] = None):
        """
        Initialize agent identity.
        
        Args:
            agent_name: Name of the agent (e.g., "orchestrator", "engineer")
            key_dir: Directory to store agent keys
        """
        if not HAS_CRYPTO:
            raise ImportError("cryptography library required. Install: pip install cryptography")
        
        self.agent_name = agent_name
        self.agent_id = str(uuid.uuid4())
        self.key_dir = key_dir or Path.home() / ".agentic-engineers" / "agents"
        
        self.private_key = None
        self.public_key = None
        self.identity_chain: List[str] = [self.agent_id]
        
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self) -> None:
        """Load existing keys or generate new keypair for this agent."""
        key_file = self.key_dir / f"{self.agent_name}_key.pem"
        pub_file = self.key_dir / f"{self.agent_name}_pub.pem"
        
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        if key_file.exists() and pub_file.exists():
            self._load_keys(key_file, pub_file)
        else:
            self._generate_keys(key_file, pub_file)
    
    def _load_keys(self, key_file: Path, pub_file: Path) -> None:
        """Load agent keys from disk."""
        try:
            with open(key_file, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            with open(pub_file, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.debug(f"Loaded agent identity keys for {self.agent_name}")
        except Exception as e:
            logger.error(f"Failed to load agent keys: {e}")
            raise
    
    def _generate_keys(self, key_file: Path, pub_file: Path) -> None:
        """Generate new RSA keypair for agent (2048-bit)."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.private_key = private_key
        self.public_key = private_key.public_key()
        
        # Save to disk
        with open(key_file, "wb") as f:
            f.write(self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        key_file.chmod(0o600)
        
        with open(pub_file, "wb") as f:
            f.write(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        logger.info(f"Generated new identity keys for {self.agent_name}")
    
    def sign_identity(self, message: Dict[str, Any]) -> str:
        """
        Sign a message with agent's private key (base64-encoded signature).
        
        Args:
            message: Message to sign
            
        Returns:
            Base64-encoded signature
        """
        import base64
        
        # Canonicalize JSON
        json_str = json.dumps(message, sort_keys=True, separators=(',', ':'))
        msg_hash = hashlib.sha256(json_str.encode()).digest()
        
        # Sign
        signature = self.private_key.sign(
            msg_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_identity_signature(self, message: Dict[str, Any], 
                                 signature: str, public_key_pem: str) -> bool:
        """
        Verify identity signature using agent's public key.
        
        Args:
            message: Original message
            signature: Signature to verify (base64-encoded)
            public_key_pem: Public key in PEM format
            
        Returns:
            True if signature is valid
        """
        import base64
        
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )
            
            # Canonicalize message
            json_str = json.dumps(message, sort_keys=True, separators=(',', ':'))
            msg_hash = hashlib.sha256(json_str.encode()).digest()
            
            # Verify
            sig_bytes = base64.b64decode(signature)
            public_key.verify(
                sig_bytes,
                msg_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.debug(f"Identity signature verification failed: {e}")
            return False
    
    def get_public_key_pem(self) -> str:
        """Export public key in PEM format."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def add_identity_to_delegate(self, delegate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add agent identity and signature to DELEGATE.
        
        Includes:
        - agent_id: Unique ID of this agent
        - agent_name: Name of this agent
        - agent_public_key: Public key for verification
        - identity_chain: Chain of agent IDs in delegation hierarchy
        - agent_signature: Signature of this message
        """
        delegate_copy = delegate.copy()
        
        # Add identity metadata
        delegate_copy['__agent_id'] = self.agent_id
        delegate_copy['__agent_name'] = self.agent_name
        delegate_copy['__agent_public_key'] = self.get_public_key_pem()
        delegate_copy['__identity_chain'] = self.identity_chain
        delegate_copy['__signed_at'] = datetime.utcnow().isoformat()
        
        # Sign the message (excluding signature field itself)
        msg_to_sign = {k: v for k, v in delegate_copy.items() 
                      if not k.startswith('__agent_signature')}
        delegate_copy['__agent_signature'] = self.sign_identity(msg_to_sign)
        
        return delegate_copy
    
    def add_identity_to_handback(self, handback: Dict[str, Any]) -> Dict[str, Any]:
        """Add agent identity and signature to HANDBACK."""
        handback_copy = handback.copy()
        
        # Add identity metadata
        handback_copy['__agent_id'] = self.agent_id
        handback_copy['__agent_name'] = self.agent_name
        handback_copy['__agent_public_key'] = self.get_public_key_pem()
        handback_copy['__identity_chain'] = self.identity_chain
        handback_copy['__signed_at'] = datetime.utcnow().isoformat()
        
        # Sign the message
        msg_to_sign = {k: v for k, v in handback_copy.items() 
                      if not k.startswith('__agent_signature')}
        handback_copy['__agent_signature'] = self.sign_identity(msg_to_sign)
        
        return handback_copy
    
    def verify_delegate_identity(self, delegate: Dict[str, Any]) -> tuple:
        """
        Verify identity and signature of a DELEGATE.
        
        Returns:
            (is_valid, agent_id, error_message)
        """
        required_fields = ['__agent_id', '__agent_name', '__agent_public_key', 
                          '__identity_chain', '__agent_signature']
        
        for field in required_fields:
            if field not in delegate:
                return False, None, f"Missing identity field: {field}"
        
        agent_id = delegate['__agent_id']
        agent_name = delegate['__agent_name']
        public_key_pem = delegate['__agent_public_key']
        signature = delegate['__agent_signature']
        
        # Verify signature
        msg_to_verify = {k: v for k, v in delegate.items() 
                        if not k.startswith('__agent_signature')}
        
        if not self.verify_identity_signature(msg_to_verify, signature, public_key_pem):
            return False, agent_id, "Invalid identity signature"
        
        return True, agent_id, None
    
    def verify_handback_identity(self, handback: Dict[str, Any]) -> tuple:
        """
        Verify identity and signature of a HANDBACK.
        
        Returns:
            (is_valid, agent_id, error_message)
        """
        required_fields = ['__agent_id', '__agent_name', '__agent_public_key', 
                          '__identity_chain', '__agent_signature']
        
        for field in required_fields:
            if field not in handback:
                return False, None, f"Missing identity field: {field}"
        
        agent_id = handback['__agent_id']
        public_key_pem = handback['__agent_public_key']
        signature = handback['__agent_signature']
        
        # Verify signature
        msg_to_verify = {k: v for k, v in handback.items() 
                        if not k.startswith('__agent_signature')}
        
        if not self.verify_identity_signature(msg_to_verify, signature, public_key_pem):
            return False, agent_id, "Invalid identity signature"
        
        return True, agent_id, None
