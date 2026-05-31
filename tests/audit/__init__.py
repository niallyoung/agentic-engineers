"""Tests for __init__.py"""

def test_audit_module_version() -> None:
    """Test that audit module has a version."""
    from src.audit import __version__
    assert __version__ == "1.0.0"
