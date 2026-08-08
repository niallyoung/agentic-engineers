"""
Comprehensive tests for the authentication module.

Tests cover JWT token generation, validation, user authentication,
token refresh, revocation, and error handling.
"""

import pytest
import time
import json
from src.auth import (
    JWTHandler,
    AuthenticationManager,
    TokenPayload,
    JWTError,
    TokenExpiredError,
    InvalidTokenError,
    AuthenticationError,
)


class TestJWTHandler:
    """Tests for JWTHandler class."""

    @pytest.fixture
    def jwt_handler(self):
        """Create a JWTHandler instance."""
        return JWTHandler(secret_key="test_secret_key_12345")

    def test_init_valid_secret(self):
        """Test initialization with valid secret key."""
        handler = JWTHandler(secret_key="valid_secret_key_12345")
        assert handler.secret_key == "valid_secret_key_12345"
        assert handler.algorithm == "HS256"

    def test_init_invalid_secret_too_short(self):
        """Test initialization with secret key that's too short."""
        with pytest.raises(ValueError, match="Secret key must be at least 16 characters"):
            JWTHandler(secret_key="short")

    def test_init_empty_secret(self):
        """Test initialization with empty secret key."""
        with pytest.raises(ValueError, match="Secret key must be at least 16 characters"):
            JWTHandler(secret_key="")

    def test_base64_url_encode_decode(self, jwt_handler):
        """Test base64url encoding and decoding."""
        original = b"test data"
        encoded = jwt_handler._base64_url_encode(original)
        decoded = jwt_handler._base64_url_decode(encoded)
        assert decoded == original

    def test_base64_url_encode_decode_with_padding(self, jwt_handler):
        """Test base64url encoding/decoding with various padding scenarios."""
        test_cases = [
            b"a",
            b"ab",
            b"abc",
            b"abcd",
            b"test data with special chars !@#$%",
        ]
        for original in test_cases:
            encoded = jwt_handler._base64_url_encode(original)
            decoded = jwt_handler._base64_url_decode(encoded)
            assert decoded == original

    def test_create_signature(self, jwt_handler):
        """Test signature creation."""
        message = "header.payload"
        signature = jwt_handler._create_signature(message)
        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_signature_deterministic(self, jwt_handler):
        """Test that signature is deterministic."""
        message = "header.payload"
        sig1 = jwt_handler._create_signature(message)
        sig2 = jwt_handler._create_signature(message)
        assert sig1 == sig2

    def test_signature_different_for_different_messages(self, jwt_handler):
        """Test that different messages produce different signatures."""
        sig1 = jwt_handler._create_signature("message1")
        sig2 = jwt_handler._create_signature("message2")
        assert sig1 != sig2

    def test_generate_access_token(self, jwt_handler):
        """Test access token generation."""
        token = jwt_handler.generate_token(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            token_type="access"
        )
        assert isinstance(token, str)
        assert token.count('.') == 2  # JWT has 3 parts

    def test_generate_refresh_token(self, jwt_handler):
        """Test refresh token generation."""
        token = jwt_handler.generate_token(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            token_type="refresh"
        )
        assert isinstance(token, str)
        assert token.count('.') == 2

    def test_validate_token_success(self, jwt_handler):
        """Test successful token validation."""
        token = jwt_handler.generate_token(
            user_id="user123",
            username="testuser",
            email="test@example.com"
        )
        payload = jwt_handler.validate_token(token)
        assert payload.user_id == "user123"
        assert payload.username == "testuser"
        assert payload.email == "test@example.com"
        assert payload.token_type == "access"

    def test_validate_token_invalid_format(self, jwt_handler):
        """Test validation of malformed token."""
        with pytest.raises(InvalidTokenError, match="Token must have 3 parts"):
            jwt_handler.validate_token("invalid.token")

    def test_validate_token_invalid_signature(self, jwt_handler):
        """Test validation with tampered signature."""
        token = jwt_handler.generate_token(
            user_id="user123",
            username="testuser",
            email="test@example.com"
        )
        parts = token.split('.')
        tampered_token = f"{parts[0]}.{parts[1]}.invalidsignature"
        
        with pytest.raises(InvalidTokenError, match="Invalid token signature"):
            jwt_handler.validate_token(tampered_token)

    def test_validate_token_invalid_payload(self, jwt_handler):
        """Test validation with invalid payload."""
        header_encoded = jwt_handler._base64_url_encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        )
        invalid_payload = jwt_handler._base64_url_encode(b"not json")
        message = f"{header_encoded}.{invalid_payload}"
        signature = jwt_handler._create_signature(message)
        token = f"{message}.{signature}"
        
        with pytest.raises(InvalidTokenError, match="Invalid token payload"):
            jwt_handler.validate_token(token)

    def test_validate_token_missing_field(self, jwt_handler):
        """Test validation with missing required field."""
        header_encoded = jwt_handler._base64_url_encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        )
        incomplete_payload = jwt_handler._base64_url_encode(
            json.dumps({"user_id": "user123"}).encode()
        )
        message = f"{header_encoded}.{incomplete_payload}"
        signature = jwt_handler._create_signature(message)
        token = f"{message}.{signature}"
        
        with pytest.raises(InvalidTokenError, match="Missing required field"):
            jwt_handler.validate_token(token)

    def test_validate_expired_token(self, jwt_handler):
        """Test validation of expired token."""
        # Create a token with past expiration
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        header_encoded = jwt_handler._base64_url_encode(
            json.dumps(header).encode()
        )
        
        payload = {
            "user_id": "user123",
            "username": "testuser",
            "email": "test@example.com",
            "iat": now - 100,
            "exp": now - 50,  # Expired 50 seconds ago
            "token_type": "access"
        }
        payload_encoded = jwt_handler._base64_url_encode(
            json.dumps(payload).encode()
        )
        
        message = f"{header_encoded}.{payload_encoded}"
        signature = jwt_handler._create_signature(message)
        token = f"{message}.{signature}"
        
        with pytest.raises(TokenExpiredError, match="Token has expired"):
            jwt_handler.validate_token(token)

    def test_token_payload_dataclass(self):
        """Test TokenPayload dataclass."""
        payload = TokenPayload(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            iat=1000,
            exp=2000,
            token_type="access"
        )
        assert payload.user_id == "user123"
        assert payload.token_type == "access"


class TestAuthenticationManager:
    """Tests for AuthenticationManager class."""

    @pytest.fixture
    def auth_manager(self):
        """Create an AuthenticationManager instance."""
        jwt_handler = JWTHandler(secret_key="test_secret_key_12345")
        return AuthenticationManager(jwt_handler)

    def test_register_user_success(self, auth_manager):
        """Test successful user registration."""
        result = auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        assert result is True
        assert "user123" in auth_manager.user_store

    def test_register_user_duplicate(self, auth_manager):
        """Test registration of duplicate user."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        with pytest.raises(AuthenticationError, match="User already exists"):
            auth_manager.register_user(
                user_id="user123",
                username="anotheruser",
                email="another@example.com",
                password="password456"
            )

    def test_authenticate_success(self, auth_manager):
        """Test successful authentication."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        access_token, refresh_token = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert access_token.count('.') == 2
        assert refresh_token.count('.') == 2

    def test_authenticate_invalid_user(self, auth_manager):
        """Test authentication with non-existent user."""
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_manager.authenticate(
                user_id="nonexistent",
                password="password123"
            )

    def test_authenticate_invalid_password(self, auth_manager):
        """Test authentication with wrong password."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_manager.authenticate(
                user_id="user123",
                password="wrongpassword"  # pragma: allowlist secret
            )

    def test_refresh_access_token_success(self, auth_manager):
        """Test successful access token refresh."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        _, refresh_token = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        new_access_token = auth_manager.refresh_access_token(refresh_token)
        assert isinstance(new_access_token, str)
        assert new_access_token.count('.') == 2

    def test_refresh_access_token_with_access_token(self, auth_manager):
        """Test refresh with access token instead of refresh token."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        access_token, _ = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        with pytest.raises(InvalidTokenError, match="Token is not a refresh token"):
            auth_manager.refresh_access_token(access_token)

    def test_refresh_revoked_token(self, auth_manager):
        """Test refresh with revoked token."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        _, refresh_token = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        auth_manager.revoke_token(refresh_token)
        
        with pytest.raises(InvalidTokenError, match="Refresh token has been revoked"):
            auth_manager.refresh_access_token(refresh_token)

    def test_revoke_token_success(self, auth_manager):
        """Test successful token revocation."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        access_token, _ = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        result = auth_manager.revoke_token(access_token)
        assert result is True
        assert access_token in auth_manager.token_blacklist

    def test_verify_access_token_success(self, auth_manager):
        """Test successful access token verification."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        access_token, _ = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        payload = auth_manager.verify_access_token(access_token)
        assert payload.user_id == "user123"
        assert payload.username == "testuser"
        assert payload.email == "test@example.com"

    def test_verify_revoked_access_token(self, auth_manager):
        """Test verification of revoked access token."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        access_token, _ = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        auth_manager.revoke_token(access_token)
        
        with pytest.raises(InvalidTokenError, match="Token has been revoked"):
            auth_manager.verify_access_token(access_token)

    def test_verify_refresh_token_as_access(self, auth_manager):
        """Test verification of refresh token as access token."""
        auth_manager.register_user(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        _, refresh_token = auth_manager.authenticate(
            user_id="user123",
            password="password123"
        )
        
        with pytest.raises(InvalidTokenError, match="Token is not an access token"):
            auth_manager.verify_access_token(refresh_token)

    def test_multiple_users(self, auth_manager):
        """Test managing multiple users."""
        # Register multiple users
        for i in range(3):
            auth_manager.register_user(
                user_id=f"user{i}",
                username=f"user{i}",
                email=f"user{i}@example.com",
                password=f"password{i}"
            )
        
        # Authenticate each user
        for i in range(3):
            access_token, _ = auth_manager.authenticate(
                user_id=f"user{i}",
                password=f"password{i}"
            )
            payload = auth_manager.verify_access_token(access_token)
            assert payload.user_id == f"user{i}"

    def test_token_expiry_times(self):
        """Test token expiry times."""
        jwt_handler = JWTHandler(secret_key="test_secret_key_12345")
        
        access_token = jwt_handler.generate_token(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            token_type="access"
        )
        
        refresh_token = jwt_handler.generate_token(
            user_id="user123",
            username="testuser",
            email="test@example.com",
            token_type="refresh"
        )
        
        access_payload = jwt_handler.validate_token(access_token)
        refresh_payload = jwt_handler.validate_token(refresh_token)
        
        # Refresh token should have longer expiry
        assert refresh_payload.exp - refresh_payload.iat > access_payload.exp - access_payload.iat


class TestExceptions:
    """Tests for custom exceptions."""

    def test_jwt_error_inheritance(self):
        """Test that custom exceptions inherit from JWTError."""
        assert issubclass(TokenExpiredError, JWTError)
        assert issubclass(InvalidTokenError, JWTError)
        assert issubclass(AuthenticationError, JWTError)

    def test_exception_raising(self):
        """Test exception raising and catching."""
        with pytest.raises(JWTError):
            raise TokenExpiredError("Token expired")
        
        with pytest.raises(JWTError):
            raise InvalidTokenError("Invalid token")
        
        with pytest.raises(JWTError):
            raise AuthenticationError("Auth failed")

    def test_validate_token_with_corrupted_base64(self):
        """Test validation with corrupted base64 data."""
        jwt_handler = JWTHandler(secret_key="test_secret_key_12345")
        # Create a token with invalid base64 characters
        token = "aaa...bbb"
        with pytest.raises(InvalidTokenError):
            jwt_handler.validate_token(token)

    def test_validate_token_reraises_jwt_error(self):
        """Test that JWTError is re-raised without wrapping."""
        jwt_handler = JWTHandler(secret_key="test_secret_key_12345")
        token = jwt_handler.generate_token(
            user_id="user123",
            username="testuser",
            email="test@example.com"
        )
        # Tamper with signature to trigger InvalidTokenError
        parts = token.split('.')
        tampered = f"{parts[0]}.{parts[1]}.invalidsig"
        
        # This should raise InvalidTokenError (a JWTError subclass)
        # and it should be re-raised, not wrapped
        with pytest.raises(InvalidTokenError):
            jwt_handler.validate_token(tampered)
