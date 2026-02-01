"""
Tests for authentication and user management.
"""

import pytest
from src.auth import hash_password, verify_password, AuthService
from src.database import DatabaseManager


class TestPasswordHashing:
    """Test suite for password hashing utilities."""
    
    def test_hash_password_consistency(self):
        """Test that same password produces same hash."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 == hash2, "Same password should produce same hash"
        assert len(hash1) == 64, "SHA-256 hash should be 64 characters (hex)"
    
    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        
        assert hash1 != hash2, "Different passwords should produce different hashes"
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "my_secure_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed), "Correct password should verify"
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "my_secure_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert not verify_password(wrong_password, hashed), "Wrong password should not verify"


class TestAuthService:
    """Test suite for authentication service."""
    
    @pytest.fixture
    def auth_service(self):
        """Create a test auth service with fresh database."""
        db = DatabaseManager()
        # Clean up test data
        with db.get_connection() as conn:
            conn.execute("DELETE FROM user_workspace_roles WHERE 1=1")
            conn.execute("DELETE FROM workspaces WHERE 1=1")
            conn.execute("DELETE FROM users WHERE 1=1")
        
        return AuthService(db)
    
    def test_register_user(self, auth_service):
        """Test user registration."""
        result = auth_service.register_user(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        
        assert result['email'] == "test@example.com"
        assert result['full_name'] == "Test User"
        assert 'user_id' in result
        assert 'workspace_id' in result
        assert result['role'] == 'Admin'
    
    def test_register_duplicate_email(self, auth_service):
        """Test that duplicate email raises error."""
        auth_service.register_user(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        
        with pytest.raises(ValueError, match="already exists"):
            auth_service.register_user(
                email="test@example.com",
                password="different_password",
                full_name="Another User"
            )
    
    def test_login_success(self, auth_service):
        """Test successful login."""
        # Register user first
        auth_service.register_user(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        
        # Login
        result = auth_service.login("test@example.com", "password123")
        
        assert result is not None
        assert result['email'] == "test@example.com"
        assert result['full_name'] == "Test User"
        assert len(result['workspaces']) > 0
    
    def test_login_wrong_password(self, auth_service):
        """Test login with wrong password."""
        # Register user first
        auth_service.register_user(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        
        # Try to login with wrong password
        result = auth_service.login("test@example.com", "wrong_password")
        
        assert result is None
    
    def test_login_nonexistent_user(self, auth_service):
        """Test login with non-existent user."""
        result = auth_service.login("nonexistent@example.com", "password123")
        
        assert result is None
    
    def test_get_user_role(self, auth_service):
        """Test getting user role in workspace."""
        # Register user
        user_info = auth_service.register_user(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        
        role = auth_service.get_user_role(
            user_info['user_id'],
            user_info['workspace_id']
        )
        
        assert role == 'Admin'
    
    def test_can_edit(self, auth_service):
        """Test edit permission check."""
        # Register user
        user_info = auth_service.register_user(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        
        # Admin should be able to edit
        assert auth_service.can_edit(user_info['user_id'], user_info['workspace_id'])
    
    def test_can_admin(self, auth_service):
        """Test admin permission check."""
        # Register user
        user_info = auth_service.register_user(
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        
        # Admin should have admin permissions
        assert auth_service.can_admin(user_info['user_id'], user_info['workspace_id'])
    
    def test_invite_user(self, auth_service):
        """Test inviting a user to workspace."""
        # Register admin user
        admin_info = auth_service.register_user(
            email="admin@example.com",
            password="password123",
            full_name="Admin User"
        )
        
        # Register another user to invite
        user_info = auth_service.register_user(
            email="user@example.com",
            password="password123",
            full_name="Regular User"
        )
        
        # Invite user to admin's workspace
        invite_result = auth_service.invite_user(
            admin_info['workspace_id'],
            "user@example.com",
            "Editor",
            admin_info['user_id']
        )
        
        assert invite_result['user_id'] == user_info['user_id']
        assert invite_result['role'] == 'Editor'
        
        # Check user's role in the workspace
        role = auth_service.get_user_role(user_info['user_id'], admin_info['workspace_id'])
        assert role == 'Editor'
    
    def test_invite_nonexistent_user(self, auth_service):
        """Test inviting a non-existent user."""
        # Register admin user
        admin_info = auth_service.register_user(
            email="admin@example.com",
            password="password123",
            full_name="Admin User"
        )
        
        # Try to invite non-existent user
        with pytest.raises(ValueError, match="not found"):
            auth_service.invite_user(
                admin_info['workspace_id'],
                "nonexistent@example.com",
                "Editor",
                admin_info['user_id']
            )
    
    def test_invite_without_admin_permission(self, auth_service):
        """Test that non-admin cannot invite users."""
        # Register admin user
        admin_info = auth_service.register_user(
            email="admin@example.com",
            password="password123",
            full_name="Admin User"
        )
        
        # Register regular user
        user_info = auth_service.register_user(
            email="user@example.com",
            password="password123",
            full_name="Regular User"
        )
        
        # Invite user as Editor (not Admin)
        auth_service.invite_user(
            admin_info['workspace_id'],
            "user@example.com",
            "Editor",
            admin_info['user_id']
        )
        
        # Register another user to try to invite
        other_user = auth_service.register_user(
            email="other@example.com",
            password="password123",
            full_name="Other User"
        )
        
        # Try to invite as non-admin
        with pytest.raises(ValueError, match="Only admins"):
            auth_service.invite_user(
                admin_info['workspace_id'],
                "other@example.com",
                "Viewer",
                user_info['user_id']
            )
