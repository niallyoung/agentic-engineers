# Authentication Module Documentation

## Overview

The authentication module (`src/auth.py`) provides a complete JWT-based authentication system for securing API endpoints. It includes token generation, validation, user management, and token lifecycle management.

## Features

- **JWT Token Support**: Industry-standard JSON Web Tokens with HS256 signing
- **Dual Token System**: Separate access and refresh tokens with different expiration times
- **User Management**: User registration and authentication
- **Token Revocation**: Blacklist-based token revocation for logout functionality
- **Comprehensive Error Handling**: Custom exceptions for different failure scenarios
- **Secure Password Handling**: SHA256 hashing (production should use bcrypt)

## Architecture

### Core Components

#### 1. **JWTHandler**
Handles low-level JWT operations including token generation and validation.

```python
from src.auth import JWTHandler

# Initialize with a secret key (minimum 16 characters)
jwt_handler = JWTHandler(secret_key="your_secret_key_here_12345")

# Generate an access token
token = jwt_handler.generate_token(
    user_id="user123",
    username="john_doe",
    email="john@example.com",
    token_type="access"
)

# Validate a token
try:
    payload = jwt_handler.validate_token(token)
    print(f"Token is valid for user: {payload.username}")
except TokenExpiredError:
    print("Token has expired")
except InvalidTokenError:
    print("Token is invalid or malformed")
```

#### 2. **AuthenticationManager**
Manages user registration, authentication, and token lifecycle.

```python
from src.auth import AuthenticationManager, JWTHandler

jwt_handler = JWTHandler(secret_key="your_secret_key_here_12345")
auth_manager = AuthenticationManager(jwt_handler)

# Register a new user
auth_manager.register_user(
    user_id="user123",
    username="john_doe",
    email="john@example.com",
    password="secure_password"
)

# Authenticate user
try:
    access_token, refresh_token = auth_manager.authenticate(
        user_id="user123",
        password="secure_password"
    )
    print(f"Access token: {access_token}")
    print(f"Refresh token: {refresh_token}")
except AuthenticationError:
    print("Authentication failed")
```

#### 3. **TokenPayload**
Dataclass representing JWT token payload.

```python
from src.auth import TokenPayload

payload = TokenPayload(
    user_id="user123",
    username="john_doe",
    email="john@example.com",
    iat=1234567890,
    exp=1234571490,
    token_type="access"
)
```

### Exception Hierarchy

```
JWTError (base exception)
├── TokenExpiredError
├── InvalidTokenError
└── AuthenticationError
```

## Usage Examples

### Basic Setup

```python
from src.auth import JWTHandler, AuthenticationManager

# Initialize components
jwt_handler = JWTHandler(secret_key="your_secret_key_minimum_16_chars")
auth_manager = AuthenticationManager(jwt_handler)
```

### User Registration and Login

```python
# Register a new user
try:
    auth_manager.register_user(
        user_id="user123",
        username="alice",
        email="alice@example.com",
        password="secure_password_123"
    )
    print("User registered successfully")
except AuthenticationError as e:
    print(f"Registration failed: {e}")

# Authenticate user
try:
    access_token, refresh_token = auth_manager.authenticate(
        user_id="user123",
        password="secure_password_123"
    )
    print("Login successful")
except AuthenticationError as e:
    print(f"Login failed: {e}")
```

### Token Verification

```python
# Verify access token
try:
    payload = auth_manager.verify_access_token(access_token)
    print(f"Token is valid for user: {payload.username}")
    # Use payload.user_id for authorization checks
except InvalidTokenError as e:
    print(f"Token verification failed: {e}")
except TokenExpiredError as e:
    print(f"Token has expired: {e}")
```

### Token Refresh

```python
# Refresh access token using refresh token
try:
    new_access_token = auth_manager.refresh_access_token(refresh_token)
    print("Access token refreshed successfully")
except InvalidTokenError as e:
    print(f"Refresh failed: {e}")
except TokenExpiredError as e:
    print(f"Refresh token has expired: {e}")
```

### Token Revocation (Logout)

```python
# Revoke a token (e.g., on logout)
auth_manager.revoke_token(access_token)
print("Token revoked successfully")

# Attempting to use revoked token will fail
try:
    auth_manager.verify_access_token(access_token)
except InvalidTokenError as e:
    print(f"Token is revoked: {e}")
```

## API Reference

### JWTHandler

#### `__init__(secret_key: str, algorithm: str = "HS256")`
Initialize JWT handler with secret key.

**Parameters:**
- `secret_key` (str): Secret key for signing (minimum 16 characters)
- `algorithm` (str): Signing algorithm (default: "HS256")

**Raises:**
- `ValueError`: If secret key is less than 16 characters

#### `generate_token(user_id: str, username: str, email: str, token_type: str = "access") -> str`
Generate a JWT token.

**Parameters:**
- `user_id` (str): Unique user identifier
- `username` (str): User's username
- `email` (str): User's email address
- `token_type` (str): "access" or "refresh" (default: "access")

**Returns:**
- JWT token string

**Token Expiry Times:**
- Access token: 1 hour (3600 seconds)
- Refresh token: 7 days (604800 seconds)

#### `validate_token(token: str) -> TokenPayload`
Validate and decode a JWT token.

**Parameters:**
- `token` (str): JWT token string

**Returns:**
- `TokenPayload` object

**Raises:**
- `InvalidTokenError`: If token is malformed or signature is invalid
- `TokenExpiredError`: If token has expired

### AuthenticationManager

#### `__init__(jwt_handler: JWTHandler)`
Initialize authentication manager.

**Parameters:**
- `jwt_handler` (JWTHandler): JWTHandler instance

#### `register_user(user_id: str, username: str, email: str, password: str) -> bool`
Register a new user.

**Parameters:**
- `user_id` (str): Unique user identifier
- `username` (str): User's username
- `email` (str): User's email address
- `password` (str): User's password

**Returns:**
- `True` if registration successful

**Raises:**
- `AuthenticationError`: If user already exists

#### `authenticate(user_id: str, password: str) -> Tuple[str, str]`
Authenticate user and return tokens.

**Parameters:**
- `user_id` (str): User identifier
- `password` (str): User password

**Returns:**
- Tuple of (access_token, refresh_token)

**Raises:**
- `AuthenticationError`: If credentials are invalid

#### `refresh_access_token(refresh_token: str) -> str`
Generate new access token from refresh token.

**Parameters:**
- `refresh_token` (str): Valid refresh token

**Returns:**
- New access token string

**Raises:**
- `InvalidTokenError`: If refresh token is invalid or revoked
- `TokenExpiredError`: If refresh token has expired

#### `revoke_token(token: str) -> bool`
Revoke a token by adding to blacklist.

**Parameters:**
- `token` (str): Token to revoke

**Returns:**
- `True` if revocation successful

#### `verify_access_token(token: str) -> TokenPayload`
Verify an access token.

**Parameters:**
- `token` (str): Access token

**Returns:**
- `TokenPayload` object

**Raises:**
- `InvalidTokenError`: If token is invalid or revoked
- `TokenExpiredError`: If token has expired

## Security Considerations

### Production Recommendations

1. **Secret Key Management**
   - Use a strong, randomly generated secret key (minimum 32 characters)
   - Store in environment variables or secure key management system
   - Rotate keys periodically

2. **Password Hashing**
   - Replace SHA256 with bcrypt or Argon2
   - Use salt for password hashing
   - Never store plaintext passwords

3. **Token Storage**
   - Store access tokens in memory or secure HTTP-only cookies
   - Never store tokens in localStorage (vulnerable to XSS)
   - Implement token rotation strategies

4. **HTTPS**
   - Always use HTTPS in production
   - Prevent token interception in transit

5. **Token Blacklist**
   - Implement persistent token blacklist (database/Redis)
   - Current implementation uses in-memory set (lost on restart)

6. **Rate Limiting**
   - Implement rate limiting on authentication endpoints
   - Prevent brute force attacks

7. **CORS**
   - Configure CORS properly to prevent unauthorized access
   - Restrict token exposure to same-origin requests

## Testing

The module includes comprehensive test coverage (99%+):

```bash
# Run all tests
python3 -m pytest tests/test_auth.py -v

# Run with coverage report
python3 -m pytest tests/test_auth.py --cov=src.auth --cov-report=html

# Run specific test class
python3 -m pytest tests/test_auth.py::TestJWTHandler -v
```

### Test Coverage

- **JWTHandler**: 17 tests covering token generation, validation, signature creation
- **AuthenticationManager**: 14 tests covering user registration, authentication, token refresh
- **Exception Handling**: 4 tests covering error scenarios

**Total: 35 tests, 99% code coverage**

## Integration with Flask/FastAPI

### Flask Example

```python
from flask import Flask, request, jsonify
from functools import wraps
from src.auth import AuthenticationManager, JWTHandler, InvalidTokenError

app = Flask(__name__)
jwt_handler = JWTHandler(secret_key=app.config['SECRET_KEY'])
auth_manager = AuthenticationManager(jwt_handler)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        try:
            payload = auth_manager.verify_access_token(token)
            request.user_id = payload.user_id
        except (InvalidTokenError, Exception) as e:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    try:
        auth_manager.register_user(
            user_id=data['user_id'],
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        return jsonify({'message': 'User registered'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    try:
        access_token, refresh_token = auth_manager.authenticate(
            user_id=data['user_id'],
            password=data['password']
        )
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
    except Exception as e:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/protected', methods=['GET'])
@token_required
def protected():
    return jsonify({'message': f'Hello {request.user_id}'}), 200
```

## Troubleshooting

### Common Issues

**InvalidTokenError: "Token must have 3 parts"**
- Token format is incorrect
- Ensure token is not truncated or corrupted

**TokenExpiredError: "Token has expired"**
- Token has exceeded its expiration time
- Use refresh token to get new access token

**AuthenticationError: "Invalid credentials"**
- User ID or password is incorrect
- Verify user is registered

**ValueError: "Secret key must be at least 16 characters"**
- Secret key is too short
- Use a longer, more secure key

## Version History

- **1.0.0** (2026-05-27): Initial release with JWT support, user management, and token lifecycle

## License

This module is part of the agentic-engineers framework.
