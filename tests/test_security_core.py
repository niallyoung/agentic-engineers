"""
Security Tests — Comprehensive test suite for PKI signing, entropy detection,
agent identity verification, audit logging, rate limiting, and budget enforcement.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Import security modules
from src.orchestration.security.pki_signer import PKISigner
from src.orchestration.security.entropy_detector import EntropyDetector
from src.orchestration.security.agent_identity import AgentIdentity
from src.orchestration.security.audit_logger import AuditLogger
from src.orchestration.security.rate_limiter import RateLimiter, BudgetEnforcer


class TestPKISigning:
    """Tests for PKI signing functionality."""
    
    def test_pki_signer_initializes(self):
        """Test PKI signer initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            signer = PKISigner(key_dir=Path(tmpdir))
            assert signer.private_key is not None
            assert signer.public_key is not None
    
    def test_sign_and_verify_payload(self):
        """Test signing and verifying a payload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            signer = PKISigner(key_dir=Path(tmpdir))
            
            payload = {
                'task_id': '2026-05-24-test-001',
                'role': 'engineer',
                'effort': 'low',
            }
            
            # Sign
            signature = signer.sign_payload(payload)
            assert signature  # Non-empty
            assert isinstance(signature, str)
            
            # Verify
            is_valid = signer.verify_signature(payload, signature)
            assert is_valid is True
    
    def test_verify_tampered_payload_fails(self):
        """Test that tampered payloads fail verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            signer = PKISigner(key_dir=Path(tmpdir))
            
            payload = {'task_id': '2026-05-24-test-001', 'role': 'engineer'}
            signature = signer.sign_payload(payload)
            
            # Tamper with payload
            tampered = {'task_id': '2026-05-24-test-002', 'role': 'engineer'}
            
            # Verification should fail
            is_valid = signer.verify_signature(tampered, signature)
            assert is_valid is False
    
    def test_add_signature_to_delegate(self):
        """Test adding signature to DELEGATE block."""
        with tempfile.TemporaryDirectory() as tmpdir:
            signer = PKISigner(key_dir=Path(tmpdir))
            
            delegate = {
                'task_id': '2026-05-24-test-001',
                'role': 'engineer',
                'effort': 'low',
            }
            
            signed = signer.add_signature_to_delegate(delegate)
            
            # Check signature fields added
            assert '__pki_signature' in signed
            assert '__pki_timestamp' in signed
            
            # Original not modified
            assert '__pki_signature' not in delegate
    
    def test_verify_delegate_signature(self):
        """Test DELEGATE signature verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            signer = PKISigner(key_dir=Path(tmpdir))
            
            delegate = {'task_id': '2026-05-24-test-001', 'role': 'engineer'}
            signed = signer.add_signature_to_delegate(delegate)
            
            is_valid, error = signer.verify_delegate_signature(signed)
            assert is_valid is True
            assert error is None
    
    def test_verify_invalid_delegate_signature(self):
        """Test verification of invalid DELEGATE signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            signer = PKISigner(key_dir=Path(tmpdir))
            
            delegate = {
                'task_id': '2026-05-24-test-001',
                '__pki_signature': 'invalid_signature_here',
            }
            
            is_valid, error = signer.verify_delegate_signature(delegate)
            assert is_valid is False
            assert error is not None


class TestEntropyDetection:
    """Tests for entropy-based credential detection."""
    
    def test_entropy_calculation(self):
        """Test entropy calculation for strings."""
        detector = EntropyDetector()
        
        # Low entropy (repeated characters)
        low = detector.calculate_entropy("aaaa")
        
        # High entropy (random)
        high = detector.calculate_entropy("x9kL7mP2qJ")
        
        assert low < high
        assert high > 3.0  # Random strings should have high entropy
    
    def test_detect_aws_access_key(self):
        """Test detection of AWS access keys."""
        detector = EntropyDetector()
        
        # Real AWS key format
        aws_key = "AKIAIOSFODNN7EXAMPLE"  # pragma: allowlist secret
        is_cred, reason = detector.detect_in_value(aws_key)
        
        assert is_cred is True
        assert "pattern" in reason.lower() or "aws" in reason.lower()
    
    def test_detect_jwt_token(self):
        """Test detection of JWT tokens."""
        detector = EntropyDetector()
        
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"  # pragma: allowlist secret
        is_cred, reason = detector.detect_in_value(jwt)
        
        assert is_cred is True
    
    def test_detect_high_entropy_in_field(self):
        """Test detection based on field name and entropy."""
        detector = EntropyDetector()
        
        # High entropy with suspicious field name
        is_cred, reason = detector.detect_in_value(
            "x9kL7mP2qJa5nB3tVc6rD2fG9hJ",
            field_name="api_key"
        )
        
        assert is_cred is True
    
    def test_exclude_hashes(self):
        """Test that legitimate hashes are excluded."""
        detector = EntropyDetector()
        
        # MD5 hash (32 hex chars)
        md5 = "5d41402abc4b2a76b9719d911017c592"
        is_cred, reason = detector.detect_in_value(md5)
        
        # Should not be flagged
        assert is_cred is False
    
    def test_scan_text_for_credentials(self):
        """Test scanning text for credentials."""
        detector = EntropyDetector()
        
        # Use patterns that will actually match
        text = "AKIAIOSFODNN7EXAMPLE\npassword=x9kL7mP2qJa5nB3tVc6rD2fG9hJ\n"  # pragma: allowlist secret
        
        findings = detector.scan_text(text)

        # Should find AWS key pattern
        assert len(findings) > 0


class TestLLMProviderCredentialDetection:
    """
    Regression tests for C4: the scanner detected only AWS `AKIA` keys and
    missed every LLM-provider secret format. Each case below was a confirmed
    MISS before the fix.
    """

    # Fixtures are assembled at runtime from fragments so that no literal
    # secret-shaped string exists in this file. GitHub push protection scans
    # source text and rejects commits containing well-formed provider keys —
    # even synthetic ones. The assembled runtime value is still a valid key
    # shape, so detection is genuinely exercised.
    _BODY_A = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2W3"
    _BODY_B = "Zq7Wm2Kd9Lp4Rt6Yv8Bn3Cx5Hj1Gf0Sa"
    _BODY_C = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
    _HEX = "9f3a2b1c7d5e4a8b6c2d1e0f3a7b9c5d"

    # (name, fragments) — joined at runtime; none are live credentials
    PROVIDER_SECRETS = [
        ("anthropic", ("sk-", "ant-", "api03-", _BODY_A, "-AA")),
        ("anthropic_admin", ("sk-", "ant-", "admin01-", _BODY_B)),
        ("openai_legacy", ("sk-", "T3BlbkFJ", _BODY_C)),
        ("openai_project", ("sk-", "proj-", _BODY_C, "u1v2w3z4")),
        ("openai_service_account", ("sk-", "svcacct-", _BODY_C)),
        ("openrouter", ("sk-", "or-", "v1-", "9f3a2b1c" * 8)),
        ("google_api", ("AIza", "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r")),
        ("google_oauth_secret", ("GOCSPX", "-", _BODY_B)),
        ("slack_bot", ("xox", "b-", "123456789012-1234567890123-", _BODY_B)),
        ("slack_webhook", ("https://hooks.", "slack.com", "/services/T02K7Lm9Q/B03Nf8Wp2/", _BODY_B)),
        ("huggingface", ("hf", "_", "AbCdEfGhIjKlMnOpQrStUvWzAbCdEfGhIj")),
        ("groq", ("gsk", "_", _BODY_C, "u1v2w3z4y5z6")),
        ("perplexity", ("pplx", "-", _BODY_C)),
        ("xai", ("xai", "-", "A1b2C3d4E5f6G7h8I9j0" * 2, "A1b2C3d4E5f6")),
        ("replicate", ("r8", "_", "AbCdEfGhIjKlMnOpQrStUvWzAbCdEfGhIjKl")),
        ("nvidia", ("nvapi", "-", _BODY_B, "2Dg4Th6Uj8Ik0")),
        ("langsmith", ("lsv2", "_pt_", "a1b2c3d4" * 4, "_9f3a2b1c7d")),
        ("gitlab", ("glpat", "-", "A1b2C3d4E5f6G7h8I9j0")),
        ("npm", ("npm", "_", "AbCdEfGhIjKlMnOpQrStUvWzAbCdEfGhIj")),
    ]

    @pytest.mark.parametrize("name,fragments", PROVIDER_SECRETS)
    def test_provider_secret_is_detected(self, name, fragments):
        """Every major provider key format must be flagged."""
        detector = EntropyDetector()
        secret = "".join(fragments)
        is_cred, reason = detector.detect_in_value(secret)
        assert is_cred is True, f"{name} secret was NOT detected"

    # Providers whose keys have no distinctive prefix are caught via the
    # env-var assignment pattern, which needs the whole line. Built at runtime
    # for the same push-protection reason as above.
    ASSIGNMENT_SECRETS = [
        ("cohere", ("COHERE", "_API_KEY = \"", _BODY_B, "2Dg4Th\"")),
        ("mistral", ("MISTRAL", "_API_KEY: ", _BODY_B)),
        ("azure_openai", ("AZURE_OPENAI", "_API_KEY=\"", _HEX, "\"")),
        ("anthropic_yaml", ("  anthropic", "_api_key: ", _BODY_B, "2Dg")),
    ]

    @pytest.mark.parametrize("name,fragments", ASSIGNMENT_SECRETS)
    def test_provider_key_assignment_is_detected(self, name, fragments):
        """Prefix-less provider keys are caught by whole-line assignment match."""
        detector = EntropyDetector()
        assert detector.scan_text("".join(fragments)), f"{name} assignment was NOT detected"

    @classmethod
    def _secret(cls, name: str) -> str:
        """Assemble a named fixture from PROVIDER_SECRETS at runtime."""
        return "".join(dict(cls.PROVIDER_SECRETS)[name])

    NON_SECRETS = [
        ("env_indirection_py", 'api_key = os.environ["ANTHROPIC_API_KEY"]'),
        ("env_indirection_yaml", "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}"),
        ("docs_placeholder", "OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"),
        ("docs_your_key", "ANTHROPIC_API_KEY=your-api-key-here"),
        ("docs_ellipsis", "export ANTHROPIC_API_KEY=sk-ant-api03-..."),
        ("var_name_reference", 'KEY_NAME = "ANTHROPIC_API_KEY"'),
        ("md5_hash", "5d41402abc4b2a76b9719d911017c592"),
        ("import_line", "from src.orchestration.security import EntropyDetector"),
        ("model_id", "claude-opus-4-5-20260101"),
        ("uuid", "6c272c00-80b8-499e-99c5-e44c9380b3e5"),
        # Regression: `oauth_token` used to match the English word "access".
        ("prose_access", "Always access task metadata through the context object"),
    ]

    @pytest.mark.parametrize("name,line", NON_SECRETS)
    def test_non_secrets_are_not_flagged(self, name, line):
        """Placeholders, env indirection and prose must not trip the scanner."""
        detector = EntropyDetector()
        findings = detector.scan_text(line)
        assert not findings, f"{name} false-positived: {findings}"

    def test_base64_exclusion_does_not_mask_secrets(self):
        """
        Regression: EXCLUSION_PATTERNS['base64_likely'] matched
        `^[A-Za-z0-9+/]{32,}={0,2}$` — i.e. exactly what a secret looks like —
        and suppressed Google API keys outright.
        """
        detector = EntropyDetector()
        google_key = self._secret("google_api")
        assert detector.is_excluded(google_key) is False
        assert detector.detect_in_value(google_key)[0] is True

    def test_exclusions_never_override_a_pattern_match(self):
        """A confirmed provider key wins even if it also looks excludable."""
        detector = EntropyDetector()
        # All-hex value that satisfies the 'hash_like' exclusion shape
        deepseek = "sk-" + self._HEX
        assert detector.matches_pattern(deepseek) is not None

    def test_allowlist_pragma_suppresses_finding(self):
        """Deliberate fixtures can be suppressed inline, and only inline."""
        detector = EntropyDetector()
        secret = self._secret("anthropic")
        assert detector.scan_text(secret)
        assert not detector.scan_text(f"{secret}  # pragma: allowlist secret")

    def test_severity_is_critical_for_provider_keys(self):
        """LLM provider keys must surface as CRITICAL so the gate blocks."""
        detector = EntropyDetector()
        findings = detector.scan_text(self._secret("anthropic"))
        assert detector.max_severity(findings) == "CRITICAL"

    def test_scan_covers_non_python_files(self):
        """
        Regression: the gate globbed `src/**/*.py`, so secrets in YAML/JSON/.env
        were never scanned.
        """
        detector = EntropyDetector()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "config.yaml").write_text(
                f"anthropic_api_key: {self._secret('anthropic')}\n"
            )
            (root / "settings.json").write_text(
                '{"google_api_key": "%s"}\n' % self._secret("google_api")
            )
            (root / ".env").write_text(f"GROQ_API_KEY={self._secret('groq')}\n")

            findings = detector.scan_directory(root)
            scanned = {Path(f['file']).name for f in findings}

            assert "config.yaml" in scanned
            assert "settings.json" in scanned
            assert ".env" in scanned

    def test_scan_skips_vendored_directories(self):
        """node_modules/.venv noise must not drown the signal."""
        detector = EntropyDetector()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vendored = root / "node_modules" / "pkg"
            vendored.mkdir(parents=True)
            (vendored / "keys.json").write_text(
                '{"k": "%s"}\n' % self._secret("anthropic")
            )
            assert detector.scan_directory(root) == []

    def test_secret_in_comment_is_detected(self):
        """Commented-out config is a common place live credentials get committed."""
        detector = EntropyDetector()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conf.py"
            path.write_text(f"# OPENAI_API_KEY={self._secret('openai_legacy')}\n")
            assert detector.scan_file(path), "secret in a comment was not detected"


class TestAgentIdentity:
    """Tests for agent identity verification."""
    
    def test_agent_identity_initializes(self):
        """Test agent identity initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            identity = AgentIdentity("orchestrator", key_dir=Path(tmpdir))
            
            assert identity.agent_name == "orchestrator"
            assert identity.agent_id is not None
            assert identity.private_key is not None
            assert identity.public_key is not None
    
    def test_sign_and_verify_identity(self):
        """Test signing and verifying identity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            identity = AgentIdentity("engineer", key_dir=Path(tmpdir))
            
            message = {'task_id': '2026-05-24-test-001', 'status': 'starting'}
            signature = identity.sign_identity(message)
            
            assert signature
            
            public_key_pem = identity.get_public_key_pem()
            is_valid = identity.verify_identity_signature(message, signature, public_key_pem)
            
            assert is_valid is True
    
    def test_add_identity_to_delegate(self):
        """Test adding identity to DELEGATE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            identity = AgentIdentity("orchestrator", key_dir=Path(tmpdir))
            
            delegate = {'task_id': '2026-05-24-test-001', 'role': 'engineer'}
            identified = identity.add_identity_to_delegate(delegate)
            
            assert '__agent_id' in identified
            assert '__agent_name' in identified
            assert '__agent_public_key' in identified
            assert '__agent_signature' in identified
            assert '__identity_chain' in identified
    
    def test_verify_delegate_identity(self):
        """Test verifying DELEGATE identity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            identity = AgentIdentity("engineer", key_dir=Path(tmpdir))
            
            delegate = {'task_id': '2026-05-24-test-001', 'role': 'engineer'}
            identified = identity.add_identity_to_delegate(delegate)
            
            is_valid, agent_id, error = identity.verify_delegate_identity(identified)
            
            assert is_valid is True
            assert agent_id is not None
            assert error is None
    
    def test_detect_spoofed_identity(self):
        """Test detection of spoofed agent identity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            identity1 = AgentIdentity("orchestrator", key_dir=Path(tmpdir))
            
            delegate = {'task_id': '2026-05-24-test-001', 'role': 'engineer'}
            identified = identity1.add_identity_to_delegate(delegate)
            
            # Tamper with agent_id
            identified['__agent_id'] = 'fake-agent-id'
            
            # Verification should fail (signature won't match)
            is_valid, agent_id, error = identity1.verify_delegate_identity(identified)
            
            assert is_valid is False


class TestAuditLogging:
    """Tests for audit logging functionality."""
    
    def test_audit_logger_initializes(self):
        """Test audit logger initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            assert logger.current_log is not None
    
    def test_log_delegate_event(self):
        """Test logging DELEGATE creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            
            delegate = {'task_id': '2026-05-24-test-001', 'effort': 'low'}
            result = logger.log_delegate('2026-05-24-test-001', delegate, 'engineer')
            
            assert result is True
            
            # Query event
            events = logger.query_events(task_id='2026-05-24-test-001')
            assert len(events) > 0
            assert events[0]['event_type'] == 'DELEGATE'
    
    def test_log_handback_event(self):
        """Test logging HANDBACK completion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            
            handback = {'tokens_in': 1000, 'tokens_out': 2000}
            result = logger.log_handback(
                '2026-05-24-test-001',
                handback,
                'engineer',
                'complete',
                95
            )
            
            assert result is True
    
    def test_log_security_check(self):
        """Test logging security check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            
            result = logger.log_security_check(
                '2026-05-24-test-001',
                'entropy_detection',
                True,
                []
            )
            
            assert result is True
    
    def test_query_audit_events(self):
        """Test querying audit events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            
            # Log multiple events
            logger.log_delegate('task-001', {}, 'engineer')
            logger.log_delegate('task-002', {}, 'engineer')
            logger.log_validation('task-001', {'passed': True, 'score': 90})
            
            # Query all events
            all_events = logger.query_events()
            assert len(all_events) >= 2
            
            # Query specific task
            task_events = logger.query_events(task_id='task-001')
            assert len(task_events) >= 1


class TestRateLimiter:
    """Tests for rate limiting functionality."""
    
    def test_rate_limiter_initializes(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()
        assert limiter.limits is not None
    
    def test_check_rate_limit_passes(self):
        """Test that rate limit check passes for low usage."""
        limiter = RateLimiter()
        
        is_allowed, reason, retry = limiter.check_rate_limit('agent-001', 'engineer')
        
        assert is_allowed is True
        assert reason is None
    
    def test_set_custom_limit(self):
        """Test setting custom rate limits."""
        limiter = RateLimiter()
        limiter.set_limit('engineer', calls_per_minute=2, calls_per_hour=10)
        
        # Use up the limit
        limiter.check_rate_limit('agent-001', 'engineer')
        limiter.check_rate_limit('agent-001', 'engineer')
        
        # Next call should fail
        is_allowed, reason, retry = limiter.check_rate_limit('agent-001', 'engineer')
        assert is_allowed is False
        assert 'exceeded' in reason.lower()
    
    def test_get_rate_limit_stats(self):
        """Test getting rate limit statistics."""
        limiter = RateLimiter()
        
        limiter.check_rate_limit('agent-001', 'engineer')
        limiter.check_rate_limit('agent-001', 'engineer')
        
        stats = limiter.get_stats('agent-001', 'engineer')
        
        assert stats['calls_in_minute'] == 2
        assert stats['headroom_minute'] > 0


class TestBudgetEnforcer:
    """Tests for budget enforcement functionality."""
    
    def test_budget_enforcer_initializes(self):
        """Test budget enforcer initialization."""
        enforcer = BudgetEnforcer()
        assert enforcer.budgets is not None
    
    def test_check_budget_passes(self):
        """Test that budget check passes for low spending."""
        enforcer = BudgetEnforcer()
        
        is_allowed, reason, remaining = enforcer.check_budget('agent-001', 'engineer', 1000)
        
        assert is_allowed is True
        assert reason is None
        assert remaining > 0
    
    def test_set_custom_budget(self):
        """Test setting custom budget limits."""
        enforcer = BudgetEnforcer()
        
        # Set very low budget
        enforcer.set_budget('engineer', per_day=100, per_week=500, per_month=2000)
        
        # Use up the limit - record spending
        is_allowed, reason, remaining = enforcer.check_budget('agent-001', 'engineer', 100)
        assert is_allowed is True
        enforcer.record_spending('agent-001', 100)
        
        # Next call should fail
        is_allowed, reason, remaining = enforcer.check_budget('agent-001', 'engineer', 10)
        assert is_allowed is False
        assert 'exceeded' in reason.lower()
    
    def test_get_spending_stats(self):
        """Test getting spending statistics."""
        enforcer = BudgetEnforcer()
        
        enforcer.check_budget('agent-001', 'engineer', 1000)
        enforcer.record_spending('agent-001', 1000)
        
        stats = enforcer.get_spending('agent-001', 'engineer')
        
        assert stats['tokens_today'] == 1000
        assert 'pct_of_daily_budget' in stats


class TestSecurityIntegration:
    """Integration tests combining multiple security components."""
    
    def test_complete_secure_delegation_flow(self):
        """Test complete secure flow: sign -> verify identity -> audit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            identity = AgentIdentity("orchestrator", key_dir=Path(tmpdir) / "identity")
            audit = AuditLogger(log_dir=Path(tmpdir) / "audit")
            
            # Create DELEGATE
            delegate = {
                'task_id': '2026-05-24-integration-001',
                'role': 'engineer',
                'effort': 'low',
                'scope': 'This is a test scope with more than 15 words to pass validation',
            }
            
            # Add identity
            delegate = identity.add_identity_to_delegate(delegate)
            
            # Log delegation
            audit.log_delegate(
                delegate['task_id'],
                delegate,
                delegate['role']
            )
            
            # Verify identity
            identity_valid, agent_id, identity_error = identity.verify_delegate_identity(delegate)
            
            assert identity_valid is True
            
            # Verify audit
            events = audit.query_events(task_id='2026-05-24-integration-001')
            assert len(events) > 0


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
