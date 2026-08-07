"""
DEPRECATED: PKI Signing — Cryptographic signature generation and verification for protocol payloads.

LOCATION: src/internal/experimental/security/pki_signer.py
STATUS: Not currently integrated into the active DELEGATE/HANDBACK lifecycle

This module was designed to ensure DELEGATE and HANDBACK blocks are cryptographically signed
and haven't been tampered with during transit. However, it is not currently wired into the
active queue orchestration or protocol validation.

To re-enable:
1. Integrate PKISigner into orchestrator_protocol_integration.py
2. Add signature generation to DELEGATE creation
3. Add signature verification to HANDBACK validation
4. Wire into quality gate checks

See: docs/architecture-security-infrastructure.md
"""

import json
import hashlib
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)

# Key storage location (should be in .github/keys on CI, local .security/ for dev)
KEY_DIR = Path.home() / ".agentic-engineers" / "security"
PRIVATE_KEY_FILE = KEY_DIR / "private_key.pem"
PUBLIC_KEY_FILE = KEY_DIR / "public_key.pem"


class PKISigner:
    """
    PKI signing and verification for DELEGATE/HANDBACK payloads.
    
    Generates RSA keypair on first use and signs all protocol payloads.
    Verifies signatures during validation to detect tampering.
    """
    
    def __init__(self, key_dir: Optional[Path] = None):
        """Initialize PKI signer with optional custom key directory."""
        if not HAS_CRYPTO:
            raise ImportError("cryptography library required for PKI signing. Install: pip install cryptography")
        
        self.key_dir = key_dir or KEY_DIR
        self.private_key = None
        self.public_key = None
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self) -> None:
        """Load existing keys or generate new keypair."""
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        private_key_file = self.key_dir / "private_key.pem"
        public_key_file = self.key_dir / "public_key.pem"
        
        if private_key_file.exists() and public_key_file.exists():
            self._load_keys(private_key_file, public_key_file)
        else:
            self._generate_keys(private_key_file, public_key_file)
            logger.info(f"Generated new RSA keypair in {self.key_dir}")
    
    def _load_keys(self, private_key_file: Path, public_key_file: Path) -> None:
        """Load RSA keys from disk."""
        try:
            with open(private_key_file, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            with open(public_key_file, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.debug("Loaded RSA keys from disk")
        except Exception as e:
            logger.error(f"Failed to load RSA keys: {e}")
            raise
    
    def _generate_keys(self, private_key_file: Path, public_key_file: Path) -> None:
        """Generate new RSA keypair (2048-bit)."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.private_key = private_key
        self.public_key = private_key.public_key()
        
        # Save to disk
        with open(private_key_file, "wb") as f:
            f.write(self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        private_key_file.chmod(0o600)  # Only readable by owner
        
        with open(public_key_file, "wb") as f:
            f.write(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        logger.info(f"Generated new RSA keypair in {self.key_dir}")
    
    def sign_payload(self, payload: Dict[str, Any]) -> str:
        """
        Sign a payload and return base64-encoded signature.
        
        Args:
            payload: Dictionary to sign (will be JSON serialized)
            
        Returns:
            Base64-encoded signature
        """
        # Canonicalize JSON for consistent hashing
        json_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        payload_hash = hashlib.sha256(json_str.encode()).digest()
        
        # Sign with private key
        signature = self.private_key.sign(
            payload_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify a signature against a payload.
        
        Args:
            payload: Dictionary that was signed
            signature: Base64-encoded signature to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Canonicalize JSON
            json_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            payload_hash = hashlib.sha256(json_str.encode()).digest()
            
            # Decode signature
            sig_bytes = base64.b64decode(signature)
            
            # Verify with public key
            self.public_key.verify(
                sig_bytes,
                payload_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.debug(f"Signature verification failed: {e}")
            return False
    
    def add_signature_to_delegate(self, delegate: Dict[str, Any]) -> Dict[str, Any]:
        """Add signature to DELEGATE block."""
        delegate_copy = delegate.copy()
        delegate_copy['__pki_signature'] = self.sign_payload(delegate)
        delegate_copy['__pki_timestamp'] = datetime.utcnow().isoformat()
        return delegate_copy
    
    def add_signature_to_handback(self, handback: Dict[str, Any]) -> Dict[str, Any]:
        """Add signature to HANDBACK block."""
        handback_copy = handback.copy()
        handback_copy['__pki_signature'] = self.sign_payload(handback)
        handback_copy['__pki_timestamp'] = datetime.utcnow().isoformat()
        return handback_copy
    
    def verify_delegate_signature(self, delegate: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Verify DELEGATE signature.
        
        Returns:
            (is_valid, error_message)
        """
        if '__pki_signature' not in delegate:
            return False, "Missing PKI signature"
        
        signature = delegate['__pki_signature']
        delegate_copy = {k: v for k, v in delegate.items() 
                        if not k.startswith('__pki_')}
        
        if not self.verify_signature(delegate_copy, signature):
            return False, "Invalid PKI signature"
        
        return True, None
    
    def verify_handback_signature(self, handback: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Verify HANDBACK signature.
        
        Returns:
            (is_valid, error_message)
        """
        if '__pki_signature' not in handback:
            return False, "Missing PKI signature"
        
        signature = handback['__pki_signature']
        handback_copy = {k: v for k, v in handback.items() 
                        if not k.startswith('__pki_')}
        
        if not self.verify_signature(handback_copy, signature):
            return False, "Invalid PKI signature"
        
        return True, None
    
    def export_public_key(self) -> str:
        """Export public key in PEM format for distribution."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
