"""
Authentication and User Management Module

Provides user registration, login, password hashing, and session management
for multi-user support in CashFlow-Local.

Author: Antigravity AI
License: MIT
"""

import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.
    
    Note: For production use, consider using bcrypt or argon2.
    SHA-256 is used here for simplicity without external dependencies.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password as hex string
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        hashed_password: Stored password hash
    
    Returns:
        True if password matches, False otherwise
    """
    return hash_password(password) == hashed_password


class AuthService:
    """
    Authentication service for user management.
    
    Handles user registration, login, and session management.
    """
    
    def __init__(self, db_manager):
        """
        Initialize authentication service.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
    
    def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        workspace_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user and optionally create a workspace.
        
        Args:
            email: User's email address (unique identifier)
            password: Plain text password (will be hashed)
            full_name: User's full name
            workspace_name: Optional workspace name to create (defaults to "{name}'s Family")
        
        Returns:
            Dictionary with user info and workspace info
        
        Raises:
            ValueError: If email already exists
        """
        # Check if user already exists
        with self.db.get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?",
                [email]
            ).fetchone()
            
            if existing:
                raise ValueError(f"User with email {email} already exists")
            
            # Hash password
            password_hash = hash_password(password)
            
            # Insert user
            conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name)
                VALUES (?, ?, ?)
                """,
                [email, password_hash, full_name]
            )
            
            # Get the newly created user
            user = conn.execute(
                "SELECT id, email, full_name FROM users WHERE email = ?",
                [email]
            ).fetchone()
            
            user_id = user[0]
            
            # Create default workspace
            if not workspace_name:
                workspace_name = f"{full_name}'s Family"
            
            conn.execute(
                """
                INSERT INTO workspaces (name, created_by)
                VALUES (?, ?)
                """,
                [workspace_name, user_id]
            )
            
            workspace = conn.execute(
                "SELECT id, name FROM workspaces WHERE created_by = ?",
                [user_id]
            ).fetchone()
            
            workspace_id = workspace[0]
            
            # Add user to workspace as Admin
            conn.execute(
                """
                INSERT INTO user_workspace_roles (user_id, workspace_id, role)
                VALUES (?, ?, 'Admin')
                """,
                [user_id, workspace_id]
            )
            
            logger.info(f"User {email} registered with workspace {workspace_name}")
            
            return {
                'user_id': user_id,
                'email': user[1],
                'full_name': user[2],
                'workspace_id': workspace_id,
                'workspace_name': workspace[1],
                'role': 'Admin'
            }
    
    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user and return their info.
        
        Args:
            email: User's email
            password: Plain text password
        
        Returns:
            User info dictionary if successful, None otherwise
        """
        with self.db.get_connection() as conn:
            user = conn.execute(
                """
                SELECT id, email, password_hash, full_name
                FROM users
                WHERE email = ?
                """,
                [email]
            ).fetchone()
            
            if not user:
                logger.warning(f"Login failed: User {email} not found")
                return None
            
            user_id, email, password_hash, full_name = user
            
            # Verify password
            if not verify_password(password, password_hash):
                logger.warning(f"Login failed: Invalid password for {email}")
                return None
            
            # Get user's workspaces
            workspaces = conn.execute(
                """
                SELECT w.id, w.name, uwr.role
                FROM workspaces w
                JOIN user_workspace_roles uwr ON w.id = uwr.workspace_id
                WHERE uwr.user_id = ?
                """,
                [user_id]
            ).fetchall()
            
            logger.info(f"User {email} logged in successfully")
            
            return {
                'user_id': user_id,
                'email': email,
                'full_name': full_name,
                'workspaces': [
                    {
                        'workspace_id': w[0],
                        'workspace_name': w[1],
                        'role': w[2]
                    }
                    for w in workspaces
                ]
            }
    
    def get_user_role(self, user_id: int, workspace_id: int) -> Optional[str]:
        """
        Get user's role in a specific workspace.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
        
        Returns:
            Role string ('Admin', 'Editor', 'Viewer') or None
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT role
                FROM user_workspace_roles
                WHERE user_id = ? AND workspace_id = ?
                """,
                [user_id, workspace_id]
            ).fetchone()
            
            return result[0] if result else None
    
    def can_edit(self, user_id: int, workspace_id: int) -> bool:
        """
        Check if user has edit permissions in workspace.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
        
        Returns:
            True if user is Admin or Editor
        """
        role = self.get_user_role(user_id, workspace_id)
        return role in ['Admin', 'Editor']
    
    def can_admin(self, user_id: int, workspace_id: int) -> bool:
        """
        Check if user has admin permissions in workspace.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
        
        Returns:
            True if user is Admin
        """
        role = self.get_user_role(user_id, workspace_id)
        return role == 'Admin'
    
    def invite_user(
        self,
        workspace_id: int,
        email: str,
        role: str,
        inviter_id: int
    ) -> Dict[str, Any]:
        """
        Invite a user to a workspace.
        
        Args:
            workspace_id: Workspace to invite to
            email: Email of user to invite
            role: Role to assign ('Admin', 'Editor', 'Viewer')
            inviter_id: User ID of person sending invite
        
        Returns:
            Invitation info
        
        Raises:
            ValueError: If inviter doesn't have admin permissions
            ValueError: If user doesn't exist
        """
        # Check if inviter is admin
        if not self.can_admin(inviter_id, workspace_id):
            raise ValueError("Only admins can invite users")
        
        if role not in ['Admin', 'Editor', 'Viewer']:
            raise ValueError(f"Invalid role: {role}")
        
        with self.db.get_connection() as conn:
            # Check if user exists
            user = conn.execute(
                "SELECT id FROM users WHERE email = ?",
                [email]
            ).fetchone()
            
            if not user:
                raise ValueError(f"User with email {email} not found")
            
            user_id = user[0]
            
            # Check if already a member
            existing = conn.execute(
                """
                SELECT id FROM user_workspace_roles
                WHERE user_id = ? AND workspace_id = ?
                """,
                [user_id, workspace_id]
            ).fetchone()
            
            if existing:
                raise ValueError("User is already a member of this workspace")
            
            # Add user to workspace
            conn.execute(
                """
                INSERT INTO user_workspace_roles (user_id, workspace_id, role)
                VALUES (?, ?, ?)
                """,
                [user_id, workspace_id, role]
            )
            
            logger.info(f"User {email} invited to workspace {workspace_id} as {role}")
            
            return {
                'user_id': user_id,
                'workspace_id': workspace_id,
                'role': role
            }
