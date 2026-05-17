"""
Authentication module providing JWT-based authentication support.

This module implements JWT token generation, validation, and middleware
for securing API endpoints. It supports both access and refresh tokens
with configurable expiration times.
"""

import json
import hmac
import hashlib
import base64
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict


@dataclass
class TokenPayload:
    """Represents a JWT token payload."""
    user_id: str
    username: str
    email: str
    iat: int  # issued at
    exp: int  # expiration time
    token_type: str = "access"  # access or refresh


class JWTError(Exception):
    """Base exception for JWT-related errors."""
    pass


class TokenExpiredError(JWTError):
    """Raised when a token has expired."""
    pass


class InvalidTokenError(JWTError):
    """Raised when a token is invalid or malformed."""
    pass


class AuthenticationError(JWTError):
    """Raised when authentication fails."""
    pass


class JWTHandler:
    """Handles JWT token generation and validation."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: Signing algorithm (default: HS256)
        """
        if not secret_key or len(secret_key) < 16:
            raise ValueError("Secret key must be at least 16 characters long")
        
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expiry = 3600  # 1 hour
        self.refresh_token_expiry = 604800  # 7 days

    def _base64_url_encode(self, data: bytes) -> str:
        """Encode bytes to base64url string."""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

    def _base64_url_decode(self, data: str) -> bytes:
        """Decode base64url string to bytes."""
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)

    def _create_signature(self, message: str) -> str:
        """Create HMAC signature for message."""
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return self._base64_url_encode(signature)

    def generate_token(
        self,
        user_id: str,
        username: str,
        email: str,
        token_type: str = "access"
    ) -> str:
        """
        Generate a JWT token.

        Args:
            user_id: User ID
            username: Username
            email: User email
            token_type: Token type (access or refresh)

        Returns:
            JWT token string
        """
        now = int(time.time())
        expiry = (
            self.access_token_expiry if token_type == "access"
            else self.refresh_token_expiry
        )

        payload = TokenPayload(
            user_id=user_id,
            username=username,
            email=email,
            iat=now,
            exp=now + expiry,
            token_type=token_type
        )

        # Create header
        header = {"alg": self.algorithm, "typ": "JWT"}
        header_encoded = self._base64_url_encode(
            json.dumps(header, separators=(',', ':')).encode()
        )

        # Create payload
        payload_dict = asdict(payload)
        payload_encoded = self._base64_url_encode(
            json.dumps(payload_dict, separators=(',', ':')).encode()
        )

        # Create signature
        message = f"{header_encoded}.{payload_encoded}"
        signature = self._create_signature(message)

        return f"{message}.{signature}"

    def validate_token(self, token: str) -> TokenPayload:
        """
        Validate and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload object

        Raises:
            InvalidTokenError: If token is malformed
            TokenExpiredError: If token has expired
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise InvalidTokenError("Token must have 3 parts")

            header_encoded, payload_encoded, signature = parts

            # Verify signature
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = self._create_signature(message)

            if not hmac.compare_digest(signature, expected_signature):
                raise InvalidTokenError("Invalid token signature")

            # Decode payload
            payload_data = json.loads(
                self._base64_url_decode(payload_encoded).decode()
            )

            # Check expiration
            now = int(time.time())
            if payload_data['exp'] < now:
                raise TokenExpiredError("Token has expired")

            return TokenPayload(**payload_data)

        except json.JSONDecodeError as e:
            raise InvalidTokenError(f"Invalid token payload: {e}")
        except KeyError as e:
            raise InvalidTokenError(f"Missing required field: {e}")
        except Exception as e:
            if isinstance(e, JWTError):
                raise
            raise InvalidTokenError(f"Token validation failed: {e}")


class AuthenticationManager:
    """Manages user authentication and token lifecycle."""

    def __init__(self, jwt_handler: JWTHandler):
        """
        Initialize authentication manager.

        Args:
            jwt_handler: JWTHandler instance
        """
        self.jwt_handler = jwt_handler
        self.user_store: Dict[str, Dict[str, str]] = {}
        self.token_blacklist: set = set()

    def register_user(
        self,
        user_id: str,
        username: str,
        email: str,
        password: str
    ) -> bool:
        """
        Register a new user.

        Args:
            user_id: Unique user ID
            username: Username
            email: User email
            password: User password (should be hashed in production)

        Returns:
            True if registration successful
        """
        if user_id in self.user_store:
            raise AuthenticationError("User already exists")

        # Hash password (simple hash for demo, use bcrypt in production)
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        self.user_store[user_id] = {
            "username": username,
            "email": email,
            "password_hash": password_hash
        }
        return True

    def authenticate(
        self,
        user_id: str,
        password: str
    ) -> Tuple[str, str]:
        """
        Authenticate user and return tokens.

        Args:
            user_id: User ID
            password: User password

        Returns:
            Tuple of (access_token, refresh_token)

        Raises:
            AuthenticationError: If authentication fails
        """
        if user_id not in self.user_store:
            raise AuthenticationError("Invalid credentials")

        user = self.user_store[user_id]
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        if user["password_hash"] != password_hash:
            raise AuthenticationError("Invalid credentials")

        access_token = self.jwt_handler.generate_token(
            user_id=user_id,
            username=user["username"],
            email=user["email"],
            token_type="access"
        )

        refresh_token = self.jwt_handler.generate_token(
            user_id=user_id,
            username=user["username"],
            email=user["email"],
            token_type="refresh"
        )

        return access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate a new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        payload = self.jwt_handler.validate_token(refresh_token)

        if payload.token_type != "refresh":
            raise InvalidTokenError("Token is not a refresh token")

        if refresh_token in self.token_blacklist:
            raise InvalidTokenError("Refresh token has been revoked")

        return self.jwt_handler.generate_token(
            user_id=payload.user_id,
            username=payload.username,
            email=payload.email,
            token_type="access"
        )

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token by adding it to blacklist.

        Args:
            token: Token to revoke

        Returns:
            True if revocation successful
        """
        self.token_blacklist.add(token)
        return True

    def verify_access_token(self, token: str) -> TokenPayload:
        """
        Verify an access token.

        Args:
            token: Access token

        Returns:
            TokenPayload object

        Raises:
            InvalidTokenError: If token is invalid or revoked
            TokenExpiredError: If token has expired
        """
        if token in self.token_blacklist:
            raise InvalidTokenError("Token has been revoked")

        payload = self.jwt_handler.validate_token(token)

        if payload.token_type != "access":
            raise InvalidTokenError("Token is not an access token")

        return payload
