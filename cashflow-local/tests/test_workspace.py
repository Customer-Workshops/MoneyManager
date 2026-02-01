"""
Tests for workspace management.
"""

import pytest
from datetime import datetime, date
from src.workspace import WorkspaceManager
from src.auth import AuthService
from src.database import DatabaseManager


class TestWorkspaceManager:
    """Test suite for workspace management."""
    
    @pytest.fixture
    def setup(self):
        """Create test setup with users and workspace."""
        db = DatabaseManager()
        
        # Clean up test data
        with db.get_connection() as conn:
            conn.execute("DELETE FROM activity_log WHERE 1=1")
            conn.execute("DELETE FROM goals WHERE 1=1")
            conn.execute("DELETE FROM accounts WHERE 1=1")
            conn.execute("DELETE FROM user_workspace_roles WHERE 1=1")
            conn.execute("DELETE FROM workspaces WHERE 1=1")
            conn.execute("DELETE FROM users WHERE 1=1")
        
        auth_service = AuthService(db)
        workspace_manager = WorkspaceManager(db)
        
        # Create test users
        admin = auth_service.register_user(
            email="admin@example.com",
            password="password123",
            full_name="Admin User",
            workspace_name="Test Workspace"
        )
        
        editor = auth_service.register_user(
            email="editor@example.com",
            password="password123",
            full_name="Editor User"
        )
        
        # Invite editor to admin's workspace
        auth_service.invite_user(
            admin['workspace_id'],
            "editor@example.com",
            "Editor",
            admin['user_id']
        )
        
        return {
            'db': db,
            'auth_service': auth_service,
            'workspace_manager': workspace_manager,
            'admin': admin,
            'editor': editor
        }
    
    def test_get_workspace_members(self, setup):
        """Test getting workspace members."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        
        members = workspace_manager.get_workspace_members(admin['workspace_id'])
        
        assert len(members) == 2
        assert any(m['email'] == 'admin@example.com' for m in members)
        assert any(m['email'] == 'editor@example.com' for m in members)
    
    def test_update_member_role(self, setup):
        """Test updating member role."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        editor = setup['editor']
        
        # Update editor to viewer
        result = workspace_manager.update_member_role(
            admin['workspace_id'],
            editor['user_id'],
            'Viewer',
            admin['user_id']
        )
        
        assert result is True
        
        # Verify role was updated
        members = workspace_manager.get_workspace_members(admin['workspace_id'])
        editor_member = next(m for m in members if m['email'] == 'editor@example.com')
        assert editor_member['role'] == 'Viewer'
    
    def test_update_member_role_without_admin(self, setup):
        """Test that non-admin cannot update roles."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        editor = setup['editor']
        
        # Try to update admin's role as editor
        with pytest.raises(ValueError, match="Only admins"):
            workspace_manager.update_member_role(
                admin['workspace_id'],
                admin['user_id'],
                'Viewer',
                editor['user_id']
            )
    
    def test_remove_member(self, setup):
        """Test removing a member from workspace."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        editor = setup['editor']
        
        # Remove editor
        result = workspace_manager.remove_member(
            admin['workspace_id'],
            editor['user_id'],
            admin['user_id']
        )
        
        assert result is True
        
        # Verify member was removed
        members = workspace_manager.get_workspace_members(admin['workspace_id'])
        assert len(members) == 1
        assert not any(m['email'] == 'editor@example.com' for m in members)
    
    def test_cannot_remove_last_admin(self, setup):
        """Test that last admin cannot be removed."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        
        # Try to remove the only admin
        with pytest.raises(ValueError, match="last admin"):
            workspace_manager.remove_member(
                admin['workspace_id'],
                admin['user_id'],
                admin['user_id']
            )
    
    def test_log_activity(self, setup):
        """Test logging activity."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        
        # Log an activity
        workspace_manager.log_activity(
            admin['workspace_id'],
            admin['user_id'],
            'created',
            'transaction',
            entity_id=123,
            description='Added new transaction'
        )
        
        # Get activity log
        activities = workspace_manager.get_activity_log(admin['workspace_id'])
        
        assert len(activities) > 0
        assert activities[0]['action'] == 'created'
        assert activities[0]['entity_type'] == 'transaction'
        assert activities[0]['entity_id'] == 123
    
    def test_create_account(self, setup):
        """Test creating an account."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        
        # Create shared account
        account_id = workspace_manager.create_account(
            admin['workspace_id'],
            'Joint Checking',
            'Checking',
            is_shared=True
        )
        
        assert account_id > 0
        
        # Verify account exists
        accounts = workspace_manager.get_accounts(admin['workspace_id'])
        assert len(accounts) == 1
        assert accounts[0]['name'] == 'Joint Checking'
        assert accounts[0]['is_shared'] is True
    
    def test_create_personal_account(self, setup):
        """Test creating a personal account."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        editor = setup['editor']
        
        # Create personal account for admin
        account_id = workspace_manager.create_account(
            admin['workspace_id'],
            'My Wallet',
            'Cash',
            is_shared=False,
            owner_user_id=admin['user_id']
        )
        
        # Admin should see it
        admin_accounts = workspace_manager.get_accounts(admin['workspace_id'], admin['user_id'])
        assert len(admin_accounts) == 1
        assert admin_accounts[0]['name'] == 'My Wallet'
        
        # Editor should not see it
        editor_accounts = workspace_manager.get_accounts(admin['workspace_id'], editor['user_id'])
        assert len(editor_accounts) == 0
    
    def test_create_goal(self, setup):
        """Test creating a savings goal."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        
        # Create goal
        goal_id = workspace_manager.create_goal(
            admin['workspace_id'],
            'Family Vacation',
            5000.0,
            target_date=date(2026, 12, 31),
            is_shared=True,
            created_by=admin['user_id']
        )
        
        assert goal_id > 0
        
        # Verify goal exists
        goals = workspace_manager.get_goals(admin['workspace_id'])
        assert len(goals) == 1
        assert goals[0]['name'] == 'Family Vacation'
        assert goals[0]['target_amount'] == 5000.0
        assert goals[0]['is_shared'] is True
    
    def test_get_goals(self, setup):
        """Test getting workspace goals."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        
        # Create multiple goals
        workspace_manager.create_goal(
            admin['workspace_id'],
            'Vacation',
            5000.0,
            is_shared=True,
            created_by=admin['user_id']
        )
        
        workspace_manager.create_goal(
            admin['workspace_id'],
            'Emergency Fund',
            10000.0,
            is_shared=True,
            created_by=admin['user_id']
        )
        
        # Get all goals
        goals = workspace_manager.get_goals(admin['workspace_id'])
        
        assert len(goals) == 2
        goal_names = [g['name'] for g in goals]
        assert 'Vacation' in goal_names
        assert 'Emergency Fund' in goal_names
    
    def test_get_activity_log(self, setup):
        """Test getting activity log with limit."""
        workspace_manager = setup['workspace_manager']
        admin = setup['admin']
        
        # Log multiple activities
        for i in range(10):
            workspace_manager.log_activity(
                admin['workspace_id'],
                admin['user_id'],
                'created',
                'transaction',
                entity_id=i,
                description=f'Transaction {i}'
            )
        
        # Get limited activities
        activities = workspace_manager.get_activity_log(admin['workspace_id'], limit=5)
        
        assert len(activities) == 5
        # Should be in reverse chronological order (newest first)
        assert activities[0]['entity_id'] == 9
