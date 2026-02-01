# Migration Guide: Single-User to Multi-User

This guide helps existing CashFlow-Local users migrate to the new multi-user system.

## What's Changed

The new multi-user system introduces:
- User authentication (email/password login)
- Workspaces for family/group financial management
- Role-based access control
- Shared and personal accounts, budgets, and goals

## Automatic Migration

When you first launch the updated application:

1. **Existing data is preserved** - All your transactions, budgets, and categories remain intact
2. **You'll see the login screen** - This is new!
3. **Create your account** - Register with your email and password
4. **Your workspace is created** - A default workspace is automatically created for you

## Manual Steps After Migration

### 1. Associate Existing Data with Your Workspace

After creating your account, your existing transactions and budgets will need to be associated with your new workspace. The application handles this automatically on first login.

### 2. Invite Family Members (Optional)

If you want to share your financial data with family members:

1. Go to **👥 Family** → **Members**
2. Click "Invite New Member"
3. Enter their email and assign a role:
   - **Admin**: Full control, can manage members
   - **Editor**: Can add transactions and budgets
   - **Viewer**: Read-only access

### 3. Configure Account Privacy

By default, all accounts are marked as "shared". If you have personal accounts:

1. Go to **👥 Family** → **Accounts**
2. For each account, decide if it should be:
   - **Shared**: Visible to all workspace members
   - **Personal**: Only visible to you

### 4. Set Up Shared vs Personal Budgets

Review your budgets and decide which should be shared:

1. Go to **💰 Budgets**
2. Shared budgets apply to all family members
3. Personal budgets only affect your transactions

## Important Notes

### Data Privacy
- All data remains local on your machine
- No data is sent to external servers
- Password hashes are stored using SHA-256

### Database Changes
The database schema has been extended with new tables:
- `users`: User accounts
- `workspaces`: Family/group workspaces
- `user_workspace_roles`: Role assignments
- `accounts`: Account management
- `goals`: Savings goals
- `activity_log`: Audit trail

### Backward Compatibility
- Existing transactions work without modification
- Old budgets are automatically converted to workspace budgets
- All categorization rules are preserved

## Troubleshooting

### "I can't log in"
- Ensure you created an account on the Registration tab
- Password is case-sensitive
- Check for typos in your email address

### "My old data isn't showing"
- Log in with the account you created
- Check that you're in the correct workspace
- Contact support if data is still missing

### "I want to use it solo (no family sharing)"
- That's fine! Just don't invite anyone
- You'll still get the benefits of user accounts and activity logging
- You can keep all accounts and budgets as "personal" if you prefer

## Rollback (If Needed)

If you need to rollback to the single-user version:

1. Stop the application
2. Check out the previous version: `git checkout <previous-commit>`
3. Your data in `data/cashflow.duckdb` will still work
4. Note: Multi-user features won't be available

## Support

For questions or issues:
- Open a GitHub issue
- Check the main README.md for documentation
- Review the application logs for error details

---

**Enjoy the new multi-user features! 🎉**
