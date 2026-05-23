"""
User profile module with bug scenario.

This module demonstrates a null pointer exception bug in profile retrieval
and the proper fix with error handling.
"""


class UserProfileError(Exception):
    """Base exception for user profile operations."""
    pass


class UserNotFoundError(UserProfileError):
    """Raised when a user is not found."""
    pass


class UserProfile:
    """User profile management with proper error handling."""

    def __init__(self):
        """Initialize the user profile storage."""
        self._users = {}

    def create_user(self, user_id, name, email):
        """Create a new user profile.
        
        Args:
            user_id: Unique user identifier
            name: User's full name
            email: User's email address
            
        Returns:
            dict: The created user profile
        """
        if not user_id or not name or not email:
            raise ValueError("user_id, name, and email are required")
        
        user = {
            "id": user_id,
            "name": name,
            "email": email,
            "preferences": {}
        }
        self._users[user_id] = user
        return user

    def get_user(self, user_id):
        """Retrieve a user profile by ID.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            dict: The user profile
            
        Raises:
            UserNotFoundError: If user does not exist
        """
        # BUGGY CODE (before fix):
        # user = self._users[user_id]
        # return user["name"].upper()  # This will fail if user is None
        
        # FIXED CODE:
        if not user_id:
            raise ValueError("user_id is required")
        
        if user_id not in self._users:
            raise UserNotFoundError(f"User with id '{user_id}' not found")
        
        user = self._users[user_id]
        if user is None:
            raise UserNotFoundError(f"User profile is corrupted for id '{user_id}'")
        
        return user

    def get_user_email(self, user_id):
        """Retrieve a user's email address.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            str: The user's email address
            
        Raises:
            UserNotFoundError: If user does not exist
        """
        user = self.get_user(user_id)
        
        if not user or "email" not in user:
            raise UserProfileError(f"Email not found for user '{user_id}'")
        
        return user["email"]

    def update_user_preferences(self, user_id, preferences):
        """Update a user's preferences.
        
        Args:
            user_id: The user's unique identifier
            preferences: Dictionary of preference key-value pairs
            
        Raises:
            UserNotFoundError: If user does not exist
            ValueError: If preferences is not a dict
        """
        if not isinstance(preferences, dict):
            raise ValueError("preferences must be a dictionary")
        
        user = self.get_user(user_id)
        user["preferences"].update(preferences)

    def delete_user(self, user_id):
        """Delete a user profile.
        
        Args:
            user_id: The user's unique identifier
            
        Raises:
            UserNotFoundError: If user does not exist
        """
        if user_id not in self._users:
            raise UserNotFoundError(f"User with id '{user_id}' not found")
        
        del self._users[user_id]

    def list_users(self):
        """List all user profiles.
        
        Returns:
            list: List of all user profiles
        """
        return list(self._users.values())
