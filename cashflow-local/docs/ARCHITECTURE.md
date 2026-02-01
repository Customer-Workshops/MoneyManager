# Multi-User Architecture

This document describes the architecture of the multi-user features in CashFlow-Local.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Page    │  │ Family Page  │  │ Activity     │      │
│  │ Login/Reg    │  │ Members/     │  │ Log          │      │
│  │              │  │ Accounts/    │  │              │      │
│  │              │  │ Goals        │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Dashboard    │  │ Transactions │  │ Budgets      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ AuthService  │  │ Workspace    │  │ Database     │      │
│  │ - register() │  │ Manager      │  │ Manager      │      │
│  │ - login()    │  │ - accounts() │  │              │      │
│  │ - invite()   │  │ - goals()    │  │              │      │
│  │ - roles()    │  │ - activity() │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      DuckDB Database                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ users        │  │ workspaces   │  │ user_        │      │
│  │              │  │              │  │ workspace_   │      │
│  │              │  │              │  │ roles        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ transactions │  │ budgets      │  │ accounts     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ goals        │  │ activity_log │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### User Registration
```
User → auth_page.py → AuthService.register_user() 
  → Create user in DB
  → Create default workspace
  → Add user as Admin to workspace
  → Auto-login
```

### User Login
```
User → auth_page.py → AuthService.login()
  → Verify password hash
  → Fetch user's workspaces
  → Store in session_state
  → Show main app
```

### Creating a Shared Account
```
Admin/Editor → family_page.py → WorkspaceManager.create_account()
  → Insert into accounts table
  → Set is_shared = True
  → Log activity
```

### Inviting a Member
```
Admin → family_page.py → AuthService.invite_user()
  → Check inviter is Admin
  → Check user exists
  → Add to user_workspace_roles
  → Log activity
```

## Database Schema

### Core Multi-User Tables

**users**
- id (PK)
- email (unique)
- password_hash
- full_name
- avatar_url
- created_at

**workspaces**
- id (PK)
- name
- created_by (FK → users)
- created_at

**user_workspace_roles**
- id (PK)
- user_id (FK → users)
- workspace_id (FK → workspaces)
- role (Admin/Editor/Viewer)
- created_at
- UNIQUE(user_id, workspace_id)

### Extended Tables

**accounts**
- id (PK)
- workspace_id (FK → workspaces)
- name
- account_type
- is_shared (boolean)
- owner_user_id (FK → users, nullable)
- created_at

**budgets**
- id (PK)
- workspace_id (FK → workspaces)
- category
- monthly_limit
- is_shared (boolean)
- owner_user_id (FK → users, nullable)
- created_at
- UNIQUE(workspace_id, category, owner_user_id)

**transactions**
- id (PK)
- hash (unique)
- transaction_date
- description
- amount
- type
- category
- source_file_hash
- workspace_id (FK → workspaces, nullable)
- user_id (FK → users, nullable)
- account_id (FK → accounts, nullable)
- created_at

**goals**
- id (PK)
- workspace_id (FK → workspaces)
- name
- target_amount
- current_amount
- target_date
- is_shared (boolean)
- created_by (FK → users)
- created_at

**activity_log**
- id (PK)
- workspace_id (FK → workspaces)
- user_id (FK → users)
- action (created/updated/deleted/uploaded)
- entity_type (transaction/budget/goal/account)
- entity_id
- description
- created_at

## Permission System

### Role Capabilities

| Action | Admin | Editor | Viewer |
|--------|-------|--------|--------|
| View data | ✓ | ✓ | ✓ |
| Add transactions | ✓ | ✓ | ✗ |
| Edit transactions | ✓ | ✓ | ✗ |
| Delete transactions | ✓ | ✗ | ✗ |
| Create budgets | ✓ | ✓ | ✗ |
| Edit budgets | ✓ | ✓ | ✗ |
| Delete budgets | ✓ | ✗ | ✗ |
| Create accounts | ✓ | ✓ | ✗ |
| Create goals | ✓ | ✓ | ✗ |
| Invite members | ✓ | ✗ | ✗ |
| Change roles | ✓ | ✗ | ✗ |
| Remove members | ✓ | ✗ | ✗ |

### Permission Checks

```python
# In AuthService
def can_edit(user_id, workspace_id):
    role = get_user_role(user_id, workspace_id)
    return role in ['Admin', 'Editor']

def can_admin(user_id, workspace_id):
    role = get_user_role(user_id, workspace_id)
    return role == 'Admin'
```

## Session Management

Sessions are managed using Streamlit's `session_state`:

```python
st.session_state.authenticated = True/False
st.session_state.user = {
    'user_id': int,
    'email': str,
    'full_name': str,
    'workspaces': [...]
}
st.session_state.current_workspace = {
    'workspace_id': int,
    'workspace_name': str,
    'role': str
}
```

## Security Considerations

1. **Password Hashing**: SHA-256 (consider bcrypt for production)
2. **Session Security**: Server-side sessions via Streamlit
3. **SQL Injection**: Parameterized queries throughout
4. **Local-First**: No data sent to external servers
5. **Role-Based Access**: Enforced at service layer

## Scalability

- **DuckDB**: Handles 100k+ transactions efficiently
- **Columnar Storage**: Optimized for analytical queries
- **Indexed Lookups**: O(1) hash-based deduplication
- **Workspace Isolation**: Queries scoped by workspace_id

## Future Enhancements

1. **OAuth Integration**: Google/Facebook login
2. **Real-Time Sync**: WebSocket updates for multi-device
3. **Notifications**: Email/push for budget alerts
4. **Advanced Permissions**: Custom roles
5. **Audit Export**: Download activity logs as CSV
6. **Profile Pictures**: Upload and display avatars
7. **Backup/Restore**: Automated workspace backups
