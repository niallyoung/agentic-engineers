"""
Entropy Detector — Credential detection using entropy analysis and pattern matching.

Identifies high-entropy strings that likely represent secrets (API keys, tokens,
database passwords, etc.) to prevent credential leakage in commits.
"""

import re
import math
import logging
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Credential patterns - high specificity
CREDENTIAL_PATTERNS = {
    'aws_access_key': re.compile(r'AKIA[0-9A-Z]{16}'),
    'aws_secret_key': re.compile(r'aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}'),
    'github_token': re.compile(r'gh[ousp]_[A-Za-z0-9_]{36,255}'),
    'azure_key': re.compile(r'[A-Za-z0-9+/]{88}=='),
    'private_key_header': re.compile(r'-----BEGIN (RSA|DSA|EC|OPENSSH|PRIVATE) KEY-----'),
    'db_password': re.compile(r'(password|passwd|pwd)\s*[:=]\s*[\'"]?([a-zA-Z0-9!@#$%^&*()_+=\-\[\]{};:,.<>?/~`]{8,})'),
    'api_key': re.compile(r'(api[_-]?key|apikey)\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})'),
    'oauth_token': re.compile(r'(access|bearer)\s+[a-zA-Z0-9\-._~+/]+=*'),
    'jwt_token': re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.'),
    'stripe_key': re.compile(r'(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}'),
}

# Legitimate high-entropy patterns to exclude
EXCLUSION_PATTERNS = {
    'base64_likely': re.compile(r'^[A-Za-z0-9+/]{32,}={0,2}$'),  # Too common
    'hash_like': re.compile(r'^[a-f0-9]{32,}$'),  # Hashes (MD5, SHA1, etc)
    'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
    'date_time': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
    'version_number': re.compile(r'^\d+\.\d+(\.\d+)?'),
    'url': re.compile(r'^https?://'),
    'hex_color': re.compile(r'^#[0-9a-fA-F]{6}$'),
}

# Field names that commonly contain secrets
SECRET_FIELD_NAMES = {
    'password', 'secret', 'token', 'api_key', 'apikey', 'api-key',
    'private_key', 'privatekey', 'private-key', 'pem', 'cert', 'certificate',
    'credential', 'credentials', 'auth', 'ssh_key', 'sshkey',
    'aws_secret_access_key', 'stripe_key', 'bearer_token',
    'jwt', 'oauth_token', 'refresh_token', 'access_token',
    'db_password', 'database_password', 'passwd', 'pwd'
}

# Minimum entropy threshold (bits per character)
# Typical random: 4-5, passwords: 2-3.5, real words: 1-1.5
MIN_ENTROPY_THRESHOLD = 3.5


class EntropyDetector:
    """
    Detect credentials in code using entropy analysis and pattern matching.
    
    Combines three detection methods:
    1. Pattern matching (specific credential formats)
    2. Entropy analysis (high entropy strings)
    3. Field name heuristics (suspicious field names containing secrets)
    """
    
    def __init__(self, entropy_threshold: float = MIN_ENTROPY_THRESHOLD):
        """
        Initialize entropy detector.
        
        Args:
            entropy_threshold: Minimum entropy (bits/char) to flag as credential
        """
        self.entropy_threshold = entropy_threshold
    
    def calculate_entropy(self, s: str) -> float:
        """
        Calculate Shannon entropy of a string (bits per character).
        
        Args:
            s: String to analyze
            
        Returns:
            Entropy in bits per character
        """
        if not s or len(s) == 0:
            return 0.0
        
        # Count character frequencies
        freq_map = {}
        for c in s:
            freq_map[c] = freq_map.get(c, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        for freq in freq_map.values():
            p = freq / len(s)
            entropy -= p * math.log2(p)
        
        # Normalize by maximum possible entropy
        max_entropy = math.log2(len(set(s)))
        
        return entropy
    
    def matches_pattern(self, value: str) -> Optional[str]:
        """
        Check if value matches known credential pattern.
        
        Returns:
            Pattern name if matched, None otherwise
        """
        for pattern_name, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(value):
                return pattern_name
        return None
    
    def is_excluded(self, value: str) -> bool:
        """Check if value should be excluded from entropy analysis."""
        for pattern in EXCLUSION_PATTERNS.values():
            if pattern.match(value):
                return True
        return False
    
    def detect_in_value(self, value: str, field_name: str = "") -> Tuple[bool, Optional[str]]:
        """
        Detect if a value is likely a credential.
        
        Args:
            value: Value to check
            field_name: Name of field containing value
            
        Returns:
            (is_credential, reason)
        """
        # Skip short strings
        if not value or len(value) < 8:
            return False, None
        
        # Check pattern matching first (highest confidence)
        pattern = self.matches_pattern(str(value))
        if pattern:
            return True, f"Matches pattern: {pattern}"
        
        # Check field name heuristics
        field_lower = field_name.lower() if field_name else ""
        if any(secret_field in field_lower for secret_field in SECRET_FIELD_NAMES):
            entropy = self.calculate_entropy(str(value))
            if entropy > 2.0:  # Lower threshold for suspicious field names
                return True, f"Suspicious field '{field_name}' with high entropy ({entropy:.2f})"
        
        # Check entropy (lowest confidence)
        if not self.is_excluded(str(value)):
            entropy = self.calculate_entropy(str(value))
            if entropy > self.entropy_threshold:
                return True, f"High entropy ({entropy:.2f} bits/char, threshold: {self.entropy_threshold})"
        
        return False, None
    
    def scan_text(self, text: str, field_name: str = "") -> List[Dict[str, any]]:
        """
        Scan text for potential credentials.
        
        Extracts potential credential strings and checks each.
        
        Args:
            text: Text to scan
            field_name: Optional field name for context
            
        Returns:
            List of findings: [{"text": str, "reason": str, "line": int}, ...]
        """
        findings = []
        
        # Split by common delimiters and check each token
        # Regex to extract tokens (alphanumeric + special chars commonly in credentials)
        token_pattern = re.compile(r"[a-zA-Z0-9+/\-_\.=:@\$%&()]{8,128}")
        
        for line_no, line in enumerate(text.split('\n'), 1):
            for match in token_pattern.finditer(line):
                token = match.group()
                is_cred, reason = self.detect_in_value(token, field_name)
                if is_cred:
                    findings.append({
                        'text': token[:20] + '...' if len(token) > 20 else token,
                        'reason': reason,
                        'line': line_no,
                        'column': match.start() + 1,
                    })
        
        return findings
    
    def scan_file(self, file_path: Path) -> List[Dict[str, any]]:
        """
        Scan a file for potential credentials.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            List of findings
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            findings = []
            for line_no, line in enumerate(content.split('\n'), 1):
                # Skip comments in code
                if line.strip().startswith('#'):
                    continue
                
                line_findings = self.scan_text(line, file_path.name)
                for finding in line_findings:
                    finding['file'] = str(file_path)
                findings.extend(line_findings)
            
            return findings
        except Exception as e:
            logger.warning(f"Failed to scan file {file_path}: {e}")
            return []
    
    def scan_dict(self, data: dict, prefix: str = "") -> List[Dict[str, any]]:
        """
        Scan a dictionary for potential credentials in values.
        
        Args:
            data: Dictionary to scan
            prefix: Key prefix for nested dicts
            
        Returns:
            List of findings
        """
        findings = []
        
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, str):
                is_cred, reason = self.detect_in_value(value, key)
                if is_cred:
                    findings.append({
                        'key': full_key,
                        'value': value[:20] + '...' if len(value) > 20 else value,
                        'reason': reason,
                    })
            elif isinstance(value, dict):
                findings.extend(self.scan_dict(value, full_key))
        
        return findings
