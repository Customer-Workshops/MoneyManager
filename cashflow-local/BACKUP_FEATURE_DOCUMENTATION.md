# 💾 Backup & Restore Feature Documentation

## Overview
The Backup & Restore feature provides users with a comprehensive solution for protecting their financial data through manual backups and flexible restore options.

## Features Implemented

### 1. Manual Backup
- **One-click download** of entire database
- **Compressed ZIP format** for efficient storage
- **SHA-256 checksum** for integrity validation
- **JSON format** for portability and readability
- Includes all:
  - Transactions
  - Category rules
  - Budget settings

### 2. Backup Validation
- Automatic validation on restore
- Checksum verification
- Format version checking
- Required field validation

### 3. Multiple Restore Modes

#### 🔄 Merge Mode (Safest)
- Adds backup data to current database
- Skips duplicate transactions (hash-based)
- Updates budgets if they exist
- Preserves existing data

#### ⚠️ Full Replace Mode
- Deletes ALL current data
- Restores complete backup
- Requires explicit confirmation
- Use with caution

#### 📅 Selective Mode
- Restore specific date range
- Filter transactions by start/end date
- Useful for partial data recovery

### 4. Backup Preview
Before restoring, users can preview:
- Total number of transactions, rules, budgets
- Date range covered
- Backup creation timestamp
- Transaction types distribution

## UI Components

### Navigation
The Backup & Restore page is accessible from the main sidebar:
```
📊 Dashboard
📤 Upload
💳 Transactions
💰 Budgets
💾 Backup & Restore  ← NEW
```

### Backup Page Layout

#### Tab 1: 📥 Create Backup
```
┌─────────────────────────────────────────────┐
│ 💾 Create Backup                            │
├─────────────────────────────────────────────┤
│                                             │
│ Create a backup of your entire database.   │
│ The backup includes:                        │
│ - All transactions                          │
│ - Category rules                            │
│ - Budget settings                           │
│                                             │
│ ┌───────────────────┐  ┌──────────────────┐│
│ │ 📥 Download Backup│  │  💡 Tip          ││
│ │     (Primary)     │  │                  ││
│ └───────────────────┘  │  Download backups││
│                        │  regularly to    ││
│ ✅ Backup created!     │  protect your    ││
│                        │  data.           ││
│ Backup Contents:       └──────────────────┘│
│ - Transactions: 150                         │
│ - Category Rules: 25                        │
│ - Budgets: 12                               │
│                                             │
│ ⬇️ Download Backup File                     │
│                                             │
└─────────────────────────────────────────────┘
```

#### Tab 2: 📤 Restore Backup
```
┌─────────────────────────────────────────────┐
│ 📤 Restore from Backup                      │
├─────────────────────────────────────────────┤
│                                             │
│ Restore your database from a previously    │
│ created backup file.                        │
│                                             │
│ ⚠️ Warning: This may modify your data       │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ 📁 Upload Backup File (ZIP)             │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ─── After upload ───                        │
│                                             │
│ �� Backup Preview                           │
│ ✅ Backup validation successful             │
│                                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│ │Transactns│ │Category  │ │ Budgets  │     │
│ │   150    │ │ Rules 25 │ │    12    │     │
│ └──────────┘ └──────────┘ └──────────┘     │
│                                             │
│ Date Range: 2024-01-01 to 2024-12-31       │
│ Backup Created: 2024-01-15 10:30:00        │
│                                             │
│ 🔧 Restore Options                          │
│                                             │
│ ○ 🔄 Merge - Add new data without removing │
│ ○ ⚠️ Full Replace - Delete all and restore  │
│ ○ 📅 Selective - Restore date range        │
│                                             │
│ [If Selective mode selected]                │
│ Start Date: [____] End Date: [____]        │
│                                             │
│ [If Full Replace mode selected]             │
│ ⚠️ WARNING: This will DELETE ALL current    │
│ data and replace it with the backup.       │
│ □ I understand this will delete all data   │
│                                             │
│ ┌───────────────────┐                       │
│ │ 🔄 Restore Database│                       │
│ └───────────────────┘                       │
│                                             │
│ ✅ Restore completed successfully!          │
│                                             │
│ Restore Summary:                            │
│ - Transactions restored: 150                │
│ - Category rules restored: 25               │
│ - Budgets restored: 12                      │
│ - Duplicates skipped: 0                     │
│                                             │
└─────────────────────────────────────────────┘
```

### Information Sections (Expandable)

#### 📖 Backup Information
- What's included in a backup
- Backup format details
- Restore modes explanation
- Best practices

#### 🔒 Security & Privacy
- Data security notes
- No automatic cloud upload
- Manual control over backups
- Future enhancements (encryption, scheduled backups, cloud integration)

## Technical Details

### Backup Format
```json
{
  "format_version": "1.0",
  "created_at": "2024-01-15T10:30:00",
  "checksum": "sha256_hash_here",
  "statistics": {
    "total_transactions": 150,
    "total_category_rules": 25,
    "total_budgets": 12
  },
  "tables": {
    "transactions": [...],
    "category_rules": [...],
    "budgets": [...]
  }
}
```

### File Structure
```
cashflow_backup_20240115_103000.zip
├── cashflow_backup_20240115_103000.json  (Main data)
└── metadata.json                          (Quick stats)
```

## Testing

### Unit Tests (9 tests - all passing ✅)
- ✅ test_create_backup
- ✅ test_validate_backup_success
- ✅ test_validate_backup_invalid_zip
- ✅ test_validate_backup_missing_tables
- ✅ test_full_restore
- ✅ test_merge_restore
- ✅ test_selective_restore
- ✅ test_get_backup_preview
- ✅ test_backup_checksum_validation

### Integration Test (✅ Passing)
- End-to-end workflow test
- Create → Validate → Preview → Restore → Verify

## User Workflow

### Creating a Backup
1. Navigate to "💾 Backup & Restore" page
2. Click "📥 Download Backup" button
3. Wait for backup creation (shows spinner)
4. Review backup statistics
5. Click "⬇️ Download Backup File" to save

### Restoring from Backup
1. Navigate to "💾 Backup & Restore" page
2. Switch to "📤 Restore Backup" tab
3. Upload your backup ZIP file
4. Review backup preview
5. Select restore mode:
   - Merge: Safest, adds without removing
   - Full Replace: Requires confirmation
   - Selective: Choose date range
6. Click "🔄 Restore Database"
7. Review restore summary

## Best Practices

1. **Regular Backups**: Create backups weekly or before major changes
2. **Multiple Locations**: Store backups in different locations
3. **Test Restores**: Periodically verify backups work
4. **Before Updates**: Always backup before app updates

## Future Enhancements (Not in MVP)
- [ ] Password encryption for backups
- [ ] Automated scheduled backups (daily/weekly)
- [ ] Cloud storage integration (Google Drive, Dropbox, AWS S3)
- [ ] Incremental backups for efficiency
- [ ] Backup history management (keep last 30)
- [ ] Email notifications for scheduled backups
