"""
Entropy Detector — Credential detection using entropy analysis and pattern matching.

Identifies high-entropy strings that likely represent secrets (API keys, tokens,
database passwords, etc.) to prevent credential leakage in commits.

NOTE (SPEC-2026-005 framework slimdown, WP-0/WP-5): this is a stdlib-only copy
of the former src/orchestration/security/entropy_detector.py, rescued here so
that .github/workflows/security-gate.yml's entropy-based credential scan keeps
working. src/orchestration/ was deleted in WP-1/WP-5 — this is now the sole
surviving copy.
"""

import re
import math
import logging
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM / AI provider credential patterns
#
# These are matched BEFORE the generic patterns below so that a finding is
# attributed to the most specific provider. Ordering matters: dict iteration
# order is insertion order, and matches_pattern() returns the first hit.
# ---------------------------------------------------------------------------
LLM_PROVIDER_PATTERNS = {
    # Anthropic — sk-ant-api03-…, sk-ant-admin01-…, sk-ant-sid01-…
    'anthropic_api_key': re.compile(r'sk-ant-[A-Za-z0-9_\-]{24,}'),

    # OpenAI — specific prefixes first, legacy `sk-` + 32+ alnum last
    'openai_project_key': re.compile(r'sk-proj-[A-Za-z0-9_\-]{20,}'),
    'openai_service_account_key': re.compile(r'sk-svcacct-[A-Za-z0-9_\-]{20,}'),
    'openai_admin_key': re.compile(r'sk-admin-[A-Za-z0-9_\-]{20,}'),
    'openrouter_api_key': re.compile(r'sk-or-v1-[A-Za-z0-9]{32,}'),
    'openai_api_key': re.compile(r'sk-[A-Za-z0-9]{32,}'),

    # Google / Gemini / Vertex
    'google_api_key': re.compile(r'AIza[0-9A-Za-z_\-]{35}'),
    'google_oauth_client_secret': re.compile(r'GOCSPX-[A-Za-z0-9_\-]{20,}'),
    'google_oauth_client_id': re.compile(r'[0-9]{10,}-[a-z0-9]{16,}\.apps\.googleusercontent\.com'),
    'gcp_service_account_json': re.compile(r'["\']type["\']\s*:\s*["\']service_account["\']'),

    # Other major model providers
    'huggingface_token': re.compile(r'\bhf_[A-Za-z0-9]{30,}'),
    'groq_api_key': re.compile(r'\bgsk_[A-Za-z0-9]{40,}'),
    'perplexity_api_key': re.compile(r'\bpplx-[A-Za-z0-9]{30,}'),
    'xai_api_key': re.compile(r'\bxai-[A-Za-z0-9]{40,}'),
    'replicate_api_token': re.compile(r'\br8_[A-Za-z0-9]{35,}'),
    'fireworks_api_key': re.compile(r'\bfw_[A-Za-z0-9]{20,}'),
    'nvidia_api_key': re.compile(r'\bnvapi-[A-Za-z0-9_\-]{40,}'),
    'anyscale_api_key': re.compile(r'\besecret_[A-Za-z0-9]{20,}'),
    'langsmith_api_key': re.compile(r'\blsv2_(pt|sk)_[a-f0-9]{32}_[a-f0-9]{10}'),

    # Generic assignment of a known LLM-provider env var. Catches .env, YAML and
    # JSON config where the value itself has no distinctive prefix (Cohere,
    # Mistral, Together, Azure OpenAI, DeepSeek, …).
    'llm_provider_key_assignment': re.compile(
        r'\b(?:ANTHROPIC|CLAUDE|OPENAI|AZURE_OPENAI|GOOGLE|GEMINI|VERTEX|COHERE|MISTRAL|'
        r'GROQ|TOGETHER|PERPLEXITY|REPLICATE|HUGGINGFACE|HUGGING_FACE|HF|DEEPSEEK|XAI|'
        r'OPENROUTER|FIREWORKS|NVIDIA|ANYSCALE|LANGSMITH|LANGCHAIN|OLLAMA|BEDROCK)'
        r'[_-]?(?:API)?[_-]?(?:KEY|TOKEN|SECRET)\s*[:=]\s*[\'"]?([A-Za-z0-9_\-\.]{16,})',
        re.IGNORECASE,
    ),
}

# Non-LLM SaaS / cloud credential patterns
CREDENTIAL_PATTERNS = {
    **LLM_PROVIDER_PATTERNS,

    'aws_access_key': re.compile(r'AKIA[0-9A-Z]{16}'),
    'aws_secret_key': re.compile(r'aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}'),
    'github_token': re.compile(r'gh[ousp]_[A-Za-z0-9_]{36,255}'),
    'gitlab_token': re.compile(r'\bglpat-[A-Za-z0-9_\-]{20,}'),
    'slack_token': re.compile(r'\bxox[baprs]-[A-Za-z0-9\-]{10,}'),
    'slack_app_token': re.compile(r'\bxapp-[0-9]-[A-Za-z0-9]+-[0-9]+-[a-f0-9]{32,}'),
    'slack_webhook': re.compile(r'https://hooks\.slack\.com/services/T[A-Za-z0-9_]+/B[A-Za-z0-9_]+/[A-Za-z0-9_]+'),
    'azure_key': re.compile(r'[A-Za-z0-9+/]{88}=='),
    'npm_token': re.compile(r'\bnpm_[A-Za-z0-9]{30,}'),
    'pypi_token': re.compile(r'\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_\-]{50,}'),
    'sendgrid_key': re.compile(r'\bSG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{40,}'),
    'twilio_key': re.compile(r'\b(?:SK|AC)[a-f0-9]{32}\b'),
    'databricks_token': re.compile(r'\bdapi[a-f0-9]{32}\b'),
    'vault_token': re.compile(r'\bhv[sb]\.[A-Za-z0-9_\-]{24,}'),
    'private_key_header': re.compile(r'-----BEGIN (RSA|DSA|EC|OPENSSH|PRIVATE) KEY-----'),
    'db_password': re.compile(r'(password|passwd|pwd)\s*[:=]\s*[\'"]([a-zA-Z0-9!@#$%^&*()_+=\-\[\]{};:,.<>?/~`]{12,})[\'"]'),
    'api_key': re.compile(r'(api[_-]?key|apikey)\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})'),
    # Bearer tokens. The previous pattern was `(access|bearer)\s+[a-zA-Z0-9\-._~+/]+=*`,
    # which matched the English word "access" followed by any word — 114 false
    # positives across this repo's prose. Now requires the literal `Bearer`
    # keyword and a 20+ char token containing at least one digit.
    'oauth_token': re.compile(r'\bBearer\s+(?=[A-Za-z0-9\-._~+/]*\d)[A-Za-z0-9\-._~+/]{20,}={0,2}'),
    'jwt_token': re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.'),
    'stripe_key': re.compile(r'(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}'),
}

# Severity per pattern. Anything not listed defaults to HIGH.
PATTERN_SEVERITY = {
    'oauth_token': 'MEDIUM',                # broad pattern, often a header example
    'api_key': 'MEDIUM',                    # generic assignment heuristic
    'db_password': 'HIGH',
    'azure_key': 'MEDIUM',                  # any 88-char base64 blob
    'twilio_key': 'MEDIUM',
}
# Every LLM provider key and private key is a CRITICAL finding.
PATTERN_SEVERITY.update({name: 'CRITICAL' for name in LLM_PROVIDER_PATTERNS})
PATTERN_SEVERITY['gcp_service_account_json'] = 'MEDIUM'  # marker only; key is separate
PATTERN_SEVERITY['private_key_header'] = 'CRITICAL'
PATTERN_SEVERITY['aws_access_key'] = 'CRITICAL'
PATTERN_SEVERITY['aws_secret_key'] = 'CRITICAL'

# Values that look like secrets but are documentation placeholders or env-var
# indirection. These suppress a match; keep them tight — every entry here is a
# hole in the scanner.
PLACEHOLDER_PATTERNS = [
    re.compile(r'x{4,}', re.IGNORECASE),                 # sk-ant-api03-xxxxxxxx
    re.compile(r'\.{3,}'),                               # sk-ant-...
    re.compile(r'(?:your|my|the)[_\-]?(?:api|key|token|secret)', re.IGNORECASE),
    re.compile(r'\b(?:example|placeholder|dummy|fake|sample|redacted|changeme|'
               r'insert|replace|todo|notreal|test[_\-]?key)\b', re.IGNORECASE),
    # Bare ENV_VAR_NAME reference. Requires an underscore so that real keys made
    # of uppercase+digits (e.g. AWS `AKIA…`) are not mistaken for a var name.
    re.compile(r'^\$?\{?[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\}?$'),
    re.compile(r'^(.)\1{7,}$'),                          # aaaaaaaa / 00000000
]

# Inline suppression for deliberate fixtures (scanner tests, documentation
# examples). Placed on the same line as the value. Kept narrow and explicit so
# that suppressions are greppable and reviewable in a diff.
ALLOWLIST_PRAGMA = re.compile(
    r'pragma:\s*allowlist\s+secret|allowlist\s+secret|noqa:\s*secret|gitleaks:\s*allow',
    re.IGNORECASE,
)

# Legitimate high-entropy patterns to exclude from ENTROPY-BASED detection only.
# NOTE: these are never consulted for pattern matches — a confirmed provider key
# is reported even if it also looks like base64 or a hash.
#
# 'base64_likely' was removed (2026-08): `^[A-Za-z0-9+/]{32,}={0,2}$` excluded
# exactly what a secret looks like, including Google `AIza…` keys and any
# base64-encoded credential. 'python_path' was narrowed from `^.*python.*$`,
# which suppressed every line containing the word "python" anywhere. 'url' was
# removed because it suppressed Slack/Discord webhook URLs.
EXCLUSION_PATTERNS = {
    'hash_like': re.compile(r'^[a-f0-9]{32,}$'),  # Hashes (MD5, SHA1, etc)
    'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
    'date_time': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
    'version_number': re.compile(r'^\d+\.\d+(\.\d+)?$'),
    'hex_color': re.compile(r'^#[0-9a-fA-F]{6}$'),
    'shebang': re.compile(r'^#!'),  # Shebang lines
    'python_path': re.compile(r'^(?:/[\w.\-]+)*/(?:python[\d.]*|site-packages)(?:/.*)?$'),
    'import_stmt': re.compile(r'^(?:from|import)\s+\S+'),  # Import statements
}

# File types worth scanning. Secrets live in config far more often than in code,
# so the scan must not be limited to *.py.
SCANNABLE_EXTENSIONS = {
    '.py', '.pyi', '.js', '.jsx', '.ts', '.tsx', '.go', '.rb', '.java', '.rs',
    '.sh', '.bash', '.zsh', '.ps1',
    '.yaml', '.yml', '.json', '.toml', '.ini', '.cfg', '.conf', '.properties',
    '.env', '.tf', '.tfvars', '.md', '.txt', '.xml', '.plist',
}

# Extensionless files that are still worth scanning.
SCANNABLE_FILENAMES = {
    '.env', '.envrc', '.npmrc', '.netrc', '.pypirc',
    'Dockerfile', 'Makefile', 'Procfile', 'credentials', 'config',
}

# Directories never worth scanning (vendored code, build output, VCS internals).
SKIP_DIRECTORIES = {
    '.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', '.tox', '.venv', 'venv', 'env', 'node_modules', 'vendor',
    'dist', 'build', 'target', '.next', '.terraform', 'htmlcov', '.eggs',
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
# Using 4.8 to avoid false positives on legitimate Python identifiers and imports
MIN_ENTROPY_THRESHOLD = 4.8


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

    def is_placeholder(self, value: str) -> bool:
        """
        Check whether a secret-shaped value is a documentation placeholder or an
        environment-variable reference rather than a live credential.
        """
        return any(p.search(value) for p in PLACEHOLDER_PATTERNS)

    def severity_for(self, pattern_name: str) -> str:
        """Severity for a matched pattern name. Unknown patterns default to HIGH."""
        return PATTERN_SEVERITY.get(pattern_name, 'HIGH')

    def matches_pattern(self, value: str) -> Optional[str]:
        """
        Check if value matches known credential pattern.

        Exclusion patterns are deliberately NOT consulted here: a confirmed
        provider key is reported even when it also looks like base64 or a hash.

        Returns:
            Pattern name if matched, None otherwise
        """
        for pattern_name, pattern in CREDENTIAL_PATTERNS.items():
            match = pattern.search(value)
            if not match:
                continue
            # Prefer the captured secret when the pattern has a capture group,
            # so `KEY=<placeholder>` is judged on the value, not the whole line.
            candidate = match.group(match.lastindex) if match.lastindex else match.group()
            if self.is_placeholder(candidate):
                continue
            return pattern_name
        return None

    def is_excluded(self, value: str) -> bool:
        """
        Check if value should be excluded from ENTROPY-BASED analysis.

        Never applied to pattern matches — see matches_pattern().
        """
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

        # Check field name heuristics ONLY (entropy unreliable)
        field_lower = field_name.lower() if field_name else ""
        if any(secret_field in field_lower for secret_field in SECRET_FIELD_NAMES):
            if self.is_excluded(str(value)) or self.is_placeholder(str(value)):
                return False, None
            entropy = self.calculate_entropy(str(value))
            if entropy > 2.5:  # Very high bar for field name heuristics only
                return True, f"Suspicious field '{field_name}' with high entropy ({entropy:.2f})"

        # NOTE: Entropy-only detection disabled (too many false positives on legitimate code)
        # Pattern matching is more reliable and specific

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
        token_pattern = re.compile(r"[a-zA-Z0-9+/\-_\.=:@\$%&()]{8,512}")

        for line_no, line in enumerate(text.split('\n'), 1):
            # Deliberate fixture / documented example — explicitly suppressed.
            if ALLOWLIST_PRAGMA.search(line):
                continue

            # Whole-line pass first: assignment-style patterns (`COHERE_API_KEY: <value>`,
            # `password = "..."`) span whitespace and can never match a single token.
            line_pattern = self.matches_pattern(line)
            if line_pattern:
                stripped = line.strip()
                findings.append({
                    'text': stripped[:40] + ('...' if len(stripped) > 40 else ''),
                    'reason': f"Matches pattern: {line_pattern}",
                    'pattern': line_pattern,
                    'severity': self.severity_for(line_pattern),
                    'line': line_no,
                    'column': 1,
                })
                continue

            for match in token_pattern.finditer(line):
                token = match.group()
                is_cred, reason = self.detect_in_value(token, field_name)
                if is_cred:
                    pattern_name = self.matches_pattern(token)
                    findings.append({
                        'text': token[:20] + '...' if len(token) > 20 else token,
                        'reason': reason,
                        'pattern': pattern_name,
                        'severity': self.severity_for(pattern_name) if pattern_name else 'MEDIUM',
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

            # NOTE: comment lines are scanned too. Commented-out config is one of
            # the most common places a live credential gets committed.
            findings = self.scan_text(content, "")
            for finding in findings:
                finding['file'] = str(file_path)

            return findings
        except Exception as e:
            logger.warning(f"Failed to scan file {file_path}: {e}")
            return []

    def should_scan(self, file_path: Path) -> bool:
        """Whether a path is a file type worth scanning for credentials."""
        if any(part in SKIP_DIRECTORIES for part in file_path.parts):
            return False
        if file_path.name in SCANNABLE_FILENAMES:
            return True
        if file_path.name.startswith('.env'):
            return True
        return file_path.suffix.lower() in SCANNABLE_EXTENSIONS

    def scan_directory(
        self,
        root: Path,
        max_file_bytes: int = 2_000_000,
    ) -> List[Dict[str, any]]:
        """
        Recursively scan a directory tree for credentials.

        Covers source, config, and data files (YAML/JSON/TOML/.env/…), not just
        Python — secrets are committed to config far more often than to code.

        Args:
            root: Directory to scan
            max_file_bytes: Skip files larger than this (generated/vendored data)

        Returns:
            List of findings, each with 'file', 'line', 'severity', 'reason'
        """
        root = Path(root)
        findings = []

        for path in sorted(root.rglob('*')):
            if not path.is_file() or not self.should_scan(path):
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    logger.debug(f"Skipping oversized file: {path}")
                    continue
            except OSError:
                continue
            findings.extend(self.scan_file(path))

        return findings

    @staticmethod
    def max_severity(findings: List[Dict[str, any]]) -> Optional[str]:
        """Highest severity present in a findings list, or None if empty."""
        order = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        present = [f.get('severity', 'MEDIUM') for f in findings]
        ranked = [s for s in order if s in present]
        return ranked[-1] if ranked else None

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
