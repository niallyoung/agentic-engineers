"""
Regression tests for user profile module.

Tests ensure that null pointer exceptions and other edge cases
are properly handled with appropriate error messages.
"""

import pytest
from user_profile import (
    UserProfile,
    UserProfileError,
    UserNotFoundError
)


class TestUserProfileCreation:
    """Test user profile creation functionality."""

    def test_create_user_success(self):
        """Test successful user creation."""
        profile = UserProfile()
        user = profile.create_user("user123", "John Doe", "john@example.com")
        
        assert user["id"] == "user123"
        assert user["name"] == "John Doe"
        assert user["email"] == "john@example.com"
        assert user["preferences"] == {}

    def test_create_user_missing_id(self):
        """Test user creation fails with missing user_id."""
        profile = UserProfile()
        
        with pytest.raises(ValueError, match="user_id, name, and email are required"):
            profile.create_user(None, "John Doe", "john@example.com")

    def test_create_user_missing_name(self):
        """Test user creation fails with missing name."""
        profile = UserProfile()
        
        with pytest.raises(ValueError, match="user_id, name, and email are required"):
            profile.create_user("user123", None, "john@example.com")

    def test_create_user_missing_email(self):
        """Test user creation fails with missing email."""
        profile = UserProfile()
        
        with pytest.raises(ValueError, match="user_id, name, and email are required"):
            profile.create_user("user123", "John Doe", None)

    def test_create_user_empty_string_id(self):
        """Test user creation fails with empty string user_id."""
        profile = UserProfile()
        
        with pytest.raises(ValueError, match="user_id, name, and email are required"):
            profile.create_user("", "John Doe", "john@example.com")


class TestUserProfileRetrieval:
    """Test user profile retrieval functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.profile = UserProfile()
        self.profile.create_user("user123", "John Doe", "john@example.com")

    def test_get_user_success(self):
        """Test successful user retrieval."""
        user = self.profile.get_user("user123")
        
        assert user["id"] == "user123"
        assert user["name"] == "John Doe"
        assert user["email"] == "john@example.com"

    def test_get_user_not_found(self):
        """Test retrieval of non-existent user raises UserNotFoundError."""
        with pytest.raises(UserNotFoundError, match="User with id 'nonexistent' not found"):
            self.profile.get_user("nonexistent")

    def test_get_user_with_none_id(self):
        """Test retrieval with None user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id is required"):
            self.profile.get_user(None)

    def test_get_user_with_empty_id(self):
        """Test retrieval with empty string user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id is required"):
            self.profile.get_user("")

    def test_get_user_null_pointer_protection(self):
        """Test that null pointer exceptions are prevented.
        
        This is the regression test for the original bug where
        accessing a None user would cause an AttributeError.
        """
        # Directly insert a None value to simulate corruption
        profile = UserProfile()
        profile._users["corrupted"] = None
        
        # Should raise UserNotFoundError, not AttributeError
        with pytest.raises(UserNotFoundError, match="User profile is corrupted"):
            profile.get_user("corrupted")


class TestUserEmailRetrieval:
    """Test user email retrieval functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.profile = UserProfile()
        self.profile.create_user("user123", "John Doe", "john@example.com")

    def test_get_user_email_success(self):
        """Test successful email retrieval."""
        email = self.profile.get_user_email("user123")
        assert email == "john@example.com"

    def test_get_user_email_not_found(self):
        """Test email retrieval for non-existent user."""
        with pytest.raises(UserNotFoundError):
            self.profile.get_user_email("nonexistent")

    def test_get_user_email_corrupted_profile(self):
        """Test email retrieval from corrupted profile."""
        profile = UserProfile()
        profile._users["corrupted"] = None
        
        with pytest.raises(UserNotFoundError, match="User profile is corrupted"):
            profile.get_user_email("corrupted")

    def test_get_user_email_missing_email_field(self):
        """Test email retrieval when email field is missing."""
        profile = UserProfile()
        profile._users["user123"] = {"id": "user123", "name": "John Doe"}
        
        with pytest.raises(UserProfileError, match="Email not found"):
            profile.get_user_email("user123")


class TestUserPreferences:
    """Test user preference management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.profile = UserProfile()
        self.profile.create_user("user123", "John Doe", "john@example.com")

    def test_update_preferences_success(self):
        """Test successful preference update."""
        self.profile.update_user_preferences("user123", {"theme": "dark", "language": "en"})
        user = self.profile.get_user("user123")
        
        assert user["preferences"]["theme"] == "dark"
        assert user["preferences"]["language"] == "en"

    def test_update_preferences_not_found(self):
        """Test preference update for non-existent user."""
        with pytest.raises(UserNotFoundError):
            self.profile.update_user_preferences("nonexistent", {"theme": "dark"})

    def test_update_preferences_invalid_type(self):
        """Test preference update with invalid type."""
        with pytest.raises(ValueError, match="preferences must be a dictionary"):
            self.profile.update_user_preferences("user123", "invalid")

    def test_update_preferences_multiple_times(self):
        """Test multiple preference updates."""
        self.profile.update_user_preferences("user123", {"theme": "dark"})
        self.profile.update_user_preferences("user123", {"language": "en"})
        
        user = self.profile.get_user("user123")
        assert user["preferences"]["theme"] == "dark"
        assert user["preferences"]["language"] == "en"


class TestUserDeletion:
    """Test user profile deletion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.profile = UserProfile()
        self.profile.create_user("user123", "John Doe", "john@example.com")
        self.profile.create_user("user456", "Jane Smith", "jane@example.com")

    def test_delete_user_success(self):
        """Test successful user deletion."""
        self.profile.delete_user("user123")
        
        with pytest.raises(UserNotFoundError):
            self.profile.get_user("user123")

    def test_delete_user_not_found(self):
        """Test deletion of non-existent user."""
        with pytest.raises(UserNotFoundError, match="User with id 'nonexistent' not found"):
            self.profile.delete_user("nonexistent")

    def test_delete_user_other_users_unaffected(self):
        """Test that deleting one user doesn't affect others."""
        self.profile.delete_user("user123")
        
        user = self.profile.get_user("user456")
        assert user["id"] == "user456"


class TestListUsers:
    """Test listing all users."""

    def test_list_users_empty(self):
        """Test listing users when none exist."""
        profile = UserProfile()
        users = profile.list_users()
        
        assert users == []

    def test_list_users_multiple(self):
        """Test listing multiple users."""
        profile = UserProfile()
        profile.create_user("user1", "User One", "user1@example.com")
        profile.create_user("user2", "User Two", "user2@example.com")
        profile.create_user("user3", "User Three", "user3@example.com")
        
        users = profile.list_users()
        assert len(users) == 3
        assert any(u["id"] == "user1" for u in users)
        assert any(u["id"] == "user2" for u in users)
        assert any(u["id"] == "user3" for u in users)


class TestErrorHandling:
    """Test comprehensive error handling."""

    def test_user_not_found_error_is_user_profile_error(self):
        """Test that UserNotFoundError is a UserProfileError."""
        assert issubclass(UserNotFoundError, UserProfileError)

    def test_error_messages_are_descriptive(self):
        """Test that error messages are descriptive."""
        profile = UserProfile()
        
        try:
            profile.get_user("missing_user")
        except UserNotFoundError as e:
            assert "missing_user" in str(e)
            assert "not found" in str(e)

    def test_null_pointer_exception_prevented(self):
        """Test that null pointer exceptions are prevented.
        
        This is the main regression test for the bug fix.
        Before the fix, accessing a None user would raise AttributeError.
        After the fix, it raises UserNotFoundError with a clear message.
        """
        profile = UserProfile()
        profile._users["broken"] = None
        
        # Should not raise AttributeError or TypeError
        with pytest.raises(UserNotFoundError):
            profile.get_user("broken")
