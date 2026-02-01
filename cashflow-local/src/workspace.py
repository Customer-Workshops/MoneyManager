"""
Workspace Management Module

Handles workspace/family operations, member management, and activity logging.

Author: Antigravity AI
License: MIT
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """
    Manages workspace operations and member management.
    """
    
    def __init__(self, db_manager):
        """
        Initialize workspace manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
    
    def get_workspace_members(self, workspace_id: int) -> List[Dict[str, Any]]:
        """
        Get all members of a workspace.
        
        Args:
            workspace_id: Workspace ID
        
        Returns:
            List of member dictionaries with user info and roles
        """
        with self.db.get_connection() as conn:
            members = conn.execute(
                """
                SELECT u.id, u.email, u.full_name, u.avatar_url, uwr.role
                FROM users u
                JOIN user_workspace_roles uwr ON u.id = uwr.user_id
                WHERE uwr.workspace_id = ?
                ORDER BY uwr.role, u.full_name
                """,
                [workspace_id]
            ).fetchall()
            
            return [
                {
                    'user_id': m[0],
                    'email': m[1],
                    'full_name': m[2],
                    'avatar_url': m[3],
                    'role': m[4]
                }
                for m in members
            ]
    
    def update_member_role(
        self,
        workspace_id: int,
        user_id: int,
        new_role: str,
        updated_by: int
    ) -> bool:
        """
        Update a member's role in a workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID to update
            new_role: New role ('Admin', 'Editor', 'Viewer')
            updated_by: User ID making the change (must be admin)
        
        Returns:
            True if successful
        
        Raises:
            ValueError: If updater is not admin or role is invalid
        """
        if new_role not in ['Admin', 'Editor', 'Viewer']:
            raise ValueError(f"Invalid role: {new_role}")
        
        # Check if updater is admin
        with self.db.get_connection() as conn:
            updater_role = conn.execute(
                """
                SELECT role FROM user_workspace_roles
                WHERE user_id = ? AND workspace_id = ?
                """,
                [updated_by, workspace_id]
            ).fetchone()
            
            if not updater_role or updater_role[0] != 'Admin':
                raise ValueError("Only admins can update member roles")
            
            # Update role
            conn.execute(
                """
                UPDATE user_workspace_roles
                SET role = ?
                WHERE user_id = ? AND workspace_id = ?
                """,
                [new_role, user_id, workspace_id]
            )
            
            logger.info(f"Updated user {user_id} role to {new_role} in workspace {workspace_id}")
            return True
    
    def remove_member(
        self,
        workspace_id: int,
        user_id: int,
        removed_by: int
    ) -> bool:
        """
        Remove a member from a workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID to remove
            removed_by: User ID making the change (must be admin)
        
        Returns:
            True if successful
        
        Raises:
            ValueError: If remover is not admin
        """
        with self.db.get_connection() as conn:
            # Check if remover is admin
            remover_role = conn.execute(
                """
                SELECT role FROM user_workspace_roles
                WHERE user_id = ? AND workspace_id = ?
                """,
                [removed_by, workspace_id]
            ).fetchone()
            
            if not remover_role or remover_role[0] != 'Admin':
                raise ValueError("Only admins can remove members")
            
            # Don't allow removing the last admin
            admin_count = conn.execute(
                """
                SELECT COUNT(*) FROM user_workspace_roles
                WHERE workspace_id = ? AND role = 'Admin'
                """,
                [workspace_id]
            ).fetchone()[0]
            
            user_role = conn.execute(
                """
                SELECT role FROM user_workspace_roles
                WHERE user_id = ? AND workspace_id = ?
                """,
                [user_id, workspace_id]
            ).fetchone()
            
            if user_role and user_role[0] == 'Admin' and admin_count <= 1:
                raise ValueError("Cannot remove the last admin from workspace")
            
            # Remove member
            conn.execute(
                """
                DELETE FROM user_workspace_roles
                WHERE user_id = ? AND workspace_id = ?
                """,
                [user_id, workspace_id]
            )
            
            logger.info(f"Removed user {user_id} from workspace {workspace_id}")
            return True
    
    def log_activity(
        self,
        workspace_id: int,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> None:
        """
        Log an activity in the workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User who performed the action
            action: Action performed (e.g., 'created', 'updated', 'deleted')
            entity_type: Type of entity (e.g., 'transaction', 'budget', 'goal')
            entity_id: ID of the entity
            description: Optional description
        """
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO activity_log (workspace_id, user_id, action, entity_type, entity_id, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [workspace_id, user_id, action, entity_type, entity_id, description]
            )
            
            logger.debug(f"Logged activity: {action} {entity_type} by user {user_id}")
    
    def get_activity_log(
        self,
        workspace_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity log for a workspace.
        
        Args:
            workspace_id: Workspace ID
            limit: Maximum number of entries to return
        
        Returns:
            List of activity log entries
        """
        with self.db.get_connection() as conn:
            activities = conn.execute(
                """
                SELECT al.id, al.action, al.entity_type, al.entity_id, al.description,
                       al.created_at, u.full_name, u.email
                FROM activity_log al
                JOIN users u ON al.user_id = u.id
                WHERE al.workspace_id = ?
                ORDER BY al.created_at DESC
                LIMIT ?
                """,
                [workspace_id, limit]
            ).fetchall()
            
            return [
                {
                    'id': a[0],
                    'action': a[1],
                    'entity_type': a[2],
                    'entity_id': a[3],
                    'description': a[4],
                    'created_at': a[5],
                    'user_name': a[6],
                    'user_email': a[7]
                }
                for a in activities
            ]
    
    def create_account(
        self,
        workspace_id: int,
        name: str,
        account_type: str,
        is_shared: bool = True,
        owner_user_id: Optional[int] = None
    ) -> int:
        """
        Create a new account (shared or personal).
        
        Args:
            workspace_id: Workspace ID
            name: Account name
            account_type: Type of account (e.g., 'Checking', 'Savings', 'Credit Card')
            is_shared: Whether account is shared with workspace
            owner_user_id: Owner if personal account
        
        Returns:
            Account ID
        """
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO accounts (workspace_id, name, account_type, is_shared, owner_user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                [workspace_id, name, account_type, is_shared, owner_user_id]
            )
            
            account_id = conn.execute(
                "SELECT id FROM accounts WHERE workspace_id = ? AND name = ? ORDER BY created_at DESC LIMIT 1",
                [workspace_id, name]
            ).fetchone()[0]
            
            logger.info(f"Created account {name} (ID: {account_id}) for workspace {workspace_id}")
            return account_id
    
    def get_accounts(self, workspace_id: int, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get accounts accessible to a user in a workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID (if provided, includes their personal accounts)
        
        Returns:
            List of account dictionaries
        """
        with self.db.get_connection() as conn:
            if user_id:
                # Get shared accounts and user's personal accounts
                accounts = conn.execute(
                    """
                    SELECT id, name, account_type, is_shared, owner_user_id
                    FROM accounts
                    WHERE workspace_id = ? AND (is_shared = TRUE OR owner_user_id = ?)
                    ORDER BY is_shared DESC, name
                    """,
                    [workspace_id, user_id]
                ).fetchall()
            else:
                # Get only shared accounts
                accounts = conn.execute(
                    """
                    SELECT id, name, account_type, is_shared, owner_user_id
                    FROM accounts
                    WHERE workspace_id = ? AND is_shared = TRUE
                    ORDER BY name
                    """,
                    [workspace_id]
                ).fetchall()
            
            return [
                {
                    'id': a[0],
                    'name': a[1],
                    'account_type': a[2],
                    'is_shared': a[3],
                    'owner_user_id': a[4]
                }
                for a in accounts
            ]
    
    def create_goal(
        self,
        workspace_id: int,
        name: str,
        target_amount: float,
        target_date: Optional[datetime] = None,
        is_shared: bool = True,
        created_by: int = None
    ) -> int:
        """
        Create a new savings goal.
        
        Args:
            workspace_id: Workspace ID
            name: Goal name
            target_amount: Target amount to save
            target_date: Optional target date
            is_shared: Whether goal is shared
            created_by: User creating the goal
        
        Returns:
            Goal ID
        """
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO goals (workspace_id, name, target_amount, target_date, is_shared, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [workspace_id, name, target_amount, target_date, is_shared, created_by]
            )
            
            goal_id = conn.execute(
                "SELECT id FROM goals WHERE workspace_id = ? AND name = ? ORDER BY created_at DESC LIMIT 1",
                [workspace_id, name]
            ).fetchone()[0]
            
            logger.info(f"Created goal {name} (ID: {goal_id}) for workspace {workspace_id}")
            return goal_id
    
    def get_goals(self, workspace_id: int) -> List[Dict[str, Any]]:
        """
        Get all goals for a workspace.
        
        Args:
            workspace_id: Workspace ID
        
        Returns:
            List of goal dictionaries
        """
        with self.db.get_connection() as conn:
            goals = conn.execute(
                """
                SELECT id, name, target_amount, current_amount, target_date, is_shared, created_by
                FROM goals
                WHERE workspace_id = ?
                ORDER BY created_at DESC
                """,
                [workspace_id]
            ).fetchall()
            
            return [
                {
                    'id': g[0],
                    'name': g[1],
                    'target_amount': float(g[2]),
                    'current_amount': float(g[3]),
                    'target_date': g[4],
                    'is_shared': g[5],
                    'created_by': g[6],
                    'progress_percent': (float(g[3]) / float(g[2]) * 100) if g[2] > 0 else 0
                }
                for g in goals
            ]
