"""
Tests for scripts/entropy_detector.py — the credential-scanning module used by
.github/workflows/security-gate.yml's "Security test execution" step
(`python3 -m pytest tests/test_security_core.py`).

The original src/orchestration/security/entropy_detector.py (and its test
coverage) was deleted in WP-1 of the framework slimdown; scripts/entropy_detector.py
is a rescued stdlib-only copy (see that module's docstring) that the security
gate now depends on exclusively, but its test coverage was never re-created —
this file closes that gap so `make test-ci` / the security-gate workflow have
real coverage of the module they invoke, not just an assumed-passing import.
"""
from pathlib import Path

import pytest

from scripts.entropy_detector import EntropyDetector

# A syntactically valid AWS access key ID shape (AKIA + 16 uppercase/digits).
# Not a real credential — deterministically matches CREDENTIAL_PATTERNS
# without depending on entropy heuristics.
FAKE_AWS_KEY = "AKIAABCDEFGHIJKLMNOP"


@pytest.fixture
def detector():
    return EntropyDetector()


class TestEntropyCalculation:
    def test_empty_string_has_zero_entropy(self, detector):
        assert detector.calculate_entropy("") == 0.0

    def test_repeated_character_has_low_entropy(self, detector):
        assert detector.calculate_entropy("aaaaaaaaaa") == 0.0

    def test_varied_characters_have_higher_entropy(self, detector):
        low = detector.calculate_entropy("aaaaaaaaaa")
        high = detector.calculate_entropy("aB3$kZ9!qL")
        assert high > low


class TestPatternMatching:
    def test_aws_access_key_is_matched(self, detector):
        assert detector.matches_pattern(FAKE_AWS_KEY) == "aws_access_key"

    def test_plain_word_does_not_match(self, detector):
        assert detector.matches_pattern("hello world") is None

    def test_placeholder_looking_value_is_not_matched(self, detector):
        # A field-shaped assignment whose value is an obvious placeholder.
        assert detector.matches_pattern("api_key = 'YOUR_API_KEY_HERE'") is None


class TestDetectInValue:
    def test_short_values_are_never_flagged(self, detector):
        is_cred, reason = detector.detect_in_value("short", field_name="password")
        assert is_cred is False
        assert reason is None

    def test_aws_key_shaped_value_is_flagged(self, detector):
        is_cred, reason = detector.detect_in_value(FAKE_AWS_KEY, field_name="key")
        assert is_cred is True
        assert "aws_access_key" in reason

    def test_ordinary_long_string_in_unrelated_field_is_not_flagged(self, detector):
        is_cred, reason = detector.detect_in_value(
            "The quick brown fox jumps over the lazy dog", field_name="description"
        )
        assert is_cred is False


class TestScanText:
    def test_scan_text_finds_embedded_credential(self, detector):
        text = f'aws_key = "{FAKE_AWS_KEY}"\nother_line = "nothing interesting here"\n'
        findings = detector.scan_text(text)
        assert any(f["reason"].find("aws_access_key") != -1 or "aws_access_key" in str(f) for f in findings)

    def test_scan_text_on_clean_text_finds_nothing(self, detector):
        findings = detector.scan_text("def add(a, b):\n    return a + b\n")
        assert findings == []


class TestScanFileAndDirectory:
    def test_should_scan_respects_extension_allowlist(self, detector, tmp_path):
        py_file = tmp_path / "module.py"
        py_file.write_text("x = 1\n")
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n")
        assert detector.should_scan(py_file) is True
        assert detector.should_scan(binary_file) is False

    def test_scan_file_detects_credential_in_real_file(self, detector, tmp_path):
        target = tmp_path / "config.env"
        target.write_text(f'AWS_ACCESS_KEY_ID="{FAKE_AWS_KEY}"\n')
        findings = detector.scan_file(target)
        assert len(findings) >= 1

    def test_scan_directory_skips_excluded_dirs(self, detector, tmp_path):
        excluded = tmp_path / "node_modules"
        excluded.mkdir()
        (excluded / "secret.env").write_text(f'KEY="{FAKE_AWS_KEY}"\n')
        findings = detector.scan_directory(tmp_path)
        assert findings == []

    def test_scan_directory_finds_credential_in_included_file(self, detector, tmp_path):
        (tmp_path / "settings.yaml").write_text(f'access_key: "{FAKE_AWS_KEY}"\n')
        findings = detector.scan_directory(tmp_path)
        assert len(findings) >= 1


class TestMaxSeverity:
    def test_max_severity_of_empty_findings_is_none(self, detector):
        assert detector.max_severity([]) is None

    def test_max_severity_picks_highest(self, detector):
        findings = [{"severity": "LOW"}, {"severity": "CRITICAL"}, {"severity": "MEDIUM"}]
        assert detector.max_severity(findings) == "CRITICAL"


def test_repo_scan_smoke():
    """Smoke test mirroring the security-gate.yml scan: running the detector
    over this repo's own source tree must not raise."""
    detector = EntropyDetector()
    repo_root = Path(__file__).resolve().parent.parent
    findings = detector.scan_directory(repo_root / "scripts")
    assert isinstance(findings, list)
