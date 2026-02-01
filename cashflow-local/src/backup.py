"""
Backup and Restore Utilities for CashFlow-Local

Provides functionality for:
- Manual database backup (full export to JSON)
- Database restore (full, selective, merge)
- Backup validation and integrity checks
- Compression support (ZIP)

Author: Antigravity AI
License: MIT
"""

import os
import json
import logging
import zipfile
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import hashlib

from src.database import db_manager

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manages database backup and restore operations.
    
    Features:
    - Full database export to JSON format
    - Compression with ZIP
    - Backup validation (checksum)
    - Multiple restore modes (full, selective, merge)
    - Backup metadata tracking
    """
    
    def __init__(self):
        """Initialize backup manager."""
        self.backup_format_version = "1.0"
    
    def create_backup(self, include_metadata: bool = True) -> Tuple[bytes, Dict[str, Any]]:
        """
        Create a full database backup as a compressed JSON file.
        
        Args:
            include_metadata: Include backup metadata (timestamp, version, etc.)
        
        Returns:
            Tuple of (zip_bytes, metadata_dict)
        
        Raises:
            Exception: If backup creation fails
        """
        try:
            logger.info("Starting database backup...")
            
            # Export all tables to dictionaries
            backup_data = {
                "format_version": self.backup_format_version,
                "created_at": datetime.now().isoformat(),
                "tables": {}
            }
            
            # Export transactions
            transactions_query = "SELECT * FROM transactions ORDER BY id"
            with db_manager.get_connection() as conn:
                transactions_df = conn.execute(transactions_query).fetchdf()
                # Convert dates to strings for JSON serialization
                transactions_df['transaction_date'] = transactions_df['transaction_date'].astype(str)
                transactions_df['created_at'] = transactions_df['created_at'].astype(str)
                backup_data['tables']['transactions'] = transactions_df.to_dict('records')
            
            # Export category_rules
            rules_query = "SELECT * FROM category_rules ORDER BY id"
            with db_manager.get_connection() as conn:
                rules_df = conn.execute(rules_query).fetchdf()
                rules_df['created_at'] = rules_df['created_at'].astype(str)
                backup_data['tables']['category_rules'] = rules_df.to_dict('records')
            
            # Export budgets
            budgets_query = "SELECT * FROM budgets ORDER BY id"
            with db_manager.get_connection() as conn:
                budgets_df = conn.execute(budgets_query).fetchdf()
                budgets_df['created_at'] = budgets_df['created_at'].astype(str)
                backup_data['tables']['budgets'] = budgets_df.to_dict('records')
            
            # Calculate statistics
            stats = {
                "total_transactions": len(backup_data['tables']['transactions']),
                "total_category_rules": len(backup_data['tables']['category_rules']),
                "total_budgets": len(backup_data['tables']['budgets'])
            }
            backup_data['statistics'] = stats
            
            # Convert to JSON
            json_str = json.dumps(backup_data, indent=2, sort_keys=True)
            json_bytes = json_str.encode('utf-8')
            
            # Calculate checksum (without the checksum field itself)
            checksum = hashlib.sha256(json_bytes).hexdigest()
            backup_data['checksum'] = checksum
            
            # Re-serialize with checksum included for final output
            json_str_with_checksum = json.dumps(backup_data, indent=2, sort_keys=True)
            
            # Create ZIP file in memory
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as zip_buffer:
                zip_buffer_name = zip_buffer.name
            
            try:
                with zipfile.ZipFile(zip_buffer_name, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Add main backup file
                    backup_filename = f"cashflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    zf.writestr(backup_filename, json_str_with_checksum)
                    
                    # Add metadata file
                    metadata = {
                        "backup_date": backup_data['created_at'],
                        "format_version": self.backup_format_version,
                        "checksum": checksum,
                        "statistics": stats
                    }
                    zf.writestr("metadata.json", json.dumps(metadata, indent=2))
                
                # Read ZIP bytes
                with open(zip_buffer_name, 'rb') as f:
                    zip_bytes = f.read()
                
                logger.info(f"Backup created successfully: {stats}")
                return zip_bytes, metadata
            
            finally:
                # Clean up temp file
                if os.path.exists(zip_buffer_name):
                    os.unlink(zip_buffer_name)
        
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise
    
    def validate_backup(self, zip_bytes: bytes) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate a backup file.
        
        Args:
            zip_bytes: Backup ZIP file bytes
        
        Returns:
            Tuple of (is_valid, message, backup_data)
        """
        try:
            # Write to temp file for extraction
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            try:
                temp_zip.write(zip_bytes)
                temp_zip.close()
                
                # Extract and validate
                with zipfile.ZipFile(temp_zip.name, 'r') as zf:
                    # Check for required files
                    files = zf.namelist()
                    json_files = [f for f in files if f.endswith('.json') and 'metadata' not in f]
                    
                    if not json_files:
                        return False, "No backup JSON file found in ZIP", None
                    
                    # Read main backup file
                    backup_json = zf.read(json_files[0]).decode('utf-8')
                    backup_data = json.loads(backup_json)
                    
                    # Validate format version
                    if 'format_version' not in backup_data:
                        return False, "Invalid backup format: missing version", None
                    
                    # Validate required fields
                    required_fields = ['created_at', 'tables']
                    for field in required_fields:
                        if field not in backup_data:
                            return False, f"Invalid backup format: missing {field}", None
                    
                    # Validate tables
                    required_tables = ['transactions', 'category_rules', 'budgets']
                    for table in required_tables:
                        if table not in backup_data['tables']:
                            return False, f"Invalid backup format: missing table {table}", None
                    
                    # Verify checksum if present
                    if 'checksum' in backup_data:
                        stored_checksum = backup_data.get('checksum')
                        # Create a copy without checksum for validation
                        data_without_checksum = {k: v for k, v in backup_data.items() if k != 'checksum'}
                        json_str = json.dumps(data_without_checksum, indent=2, sort_keys=True)
                        calculated_checksum = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
                        
                        if stored_checksum != calculated_checksum:
                            return False, "Checksum validation failed: backup may be corrupted", None
                    
                    return True, "Backup validation successful", backup_data
            
            finally:
                if os.path.exists(temp_zip.name):
                    os.unlink(temp_zip.name)
        
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}", None
        except zipfile.BadZipFile:
            return False, "Invalid ZIP file", None
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return False, f"Validation error: {e}", None
    
    def restore_backup(
        self,
        zip_bytes: bytes,
        mode: str = "full",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, int]]:
        """
        Restore database from backup.
        
        Args:
            zip_bytes: Backup ZIP file bytes
            mode: Restore mode - "full" (replace all), "merge" (add new), or "selective" (date range)
            start_date: For selective mode, start date (ISO format)
            end_date: For selective mode, end date (ISO format)
        
        Returns:
            Tuple of (success, message, statistics)
        """
        try:
            # Validate backup first
            is_valid, message, backup_data = self.validate_backup(zip_bytes)
            if not is_valid:
                return False, f"Backup validation failed: {message}", {}
            
            logger.info(f"Starting database restore (mode: {mode})...")
            
            stats = {
                "transactions_restored": 0,
                "category_rules_restored": 0,
                "budgets_restored": 0,
                "duplicates_skipped": 0
            }
            
            with db_manager.get_connection() as conn:
                # Full restore: clear existing data
                if mode == "full":
                    logger.warning("Full restore: clearing existing data...")
                    conn.execute("DELETE FROM transactions")
                    conn.execute("DELETE FROM category_rules")
                    conn.execute("DELETE FROM budgets")
                
                # Restore category_rules
                if backup_data['tables']['category_rules']:
                    for rule in backup_data['tables']['category_rules']:
                        if mode == "merge":
                            # Check if rule already exists
                            existing = conn.execute(
                                "SELECT id FROM category_rules WHERE keyword = ? AND category = ?",
                                [rule['keyword'], rule['category']]
                            ).fetchone()
                            if existing:
                                continue
                        
                        conn.execute(
                            "INSERT INTO category_rules (keyword, category) VALUES (?, ?)",
                            [rule['keyword'], rule['category']]
                        )
                        stats['category_rules_restored'] += 1
                
                # Restore budgets
                if backup_data['tables']['budgets']:
                    for budget in backup_data['tables']['budgets']:
                        if mode == "merge":
                            # Update if exists, insert if not
                            existing = conn.execute(
                                "SELECT id FROM budgets WHERE category = ?",
                                [budget['category']]
                            ).fetchone()
                            if existing:
                                conn.execute(
                                    "UPDATE budgets SET monthly_limit = ? WHERE category = ?",
                                    [budget['monthly_limit'], budget['category']]
                                )
                            else:
                                conn.execute(
                                    "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)",
                                    [budget['category'], budget['monthly_limit']]
                                )
                        else:
                            conn.execute(
                                "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)",
                                [budget['category'], budget['monthly_limit']]
                            )
                        stats['budgets_restored'] += 1
                
                # Restore transactions
                if backup_data['tables']['transactions']:
                    for txn in backup_data['tables']['transactions']:
                        # Selective restore: filter by date
                        if mode == "selective":
                            txn_date = txn['transaction_date']
                            if start_date and txn_date < start_date:
                                continue
                            if end_date and txn_date > end_date:
                                continue
                        
                        # Merge mode: check for duplicates
                        if mode == "merge":
                            existing = conn.execute(
                                "SELECT id FROM transactions WHERE hash = ?",
                                [txn['hash']]
                            ).fetchone()
                            if existing:
                                stats['duplicates_skipped'] += 1
                                continue
                        
                        # Insert transaction
                        conn.execute(
                            """
                            INSERT INTO transactions 
                            (hash, transaction_date, description, amount, type, category, source_file_hash)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            [
                                txn['hash'],
                                txn['transaction_date'],
                                txn['description'],
                                txn['amount'],
                                txn['type'],
                                txn['category'],
                                txn['source_file_hash']
                            ]
                        )
                        stats['transactions_restored'] += 1
            
            logger.info(f"Restore completed successfully: {stats}")
            return True, "Restore completed successfully", stats
        
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False, f"Restore failed: {e}", {}
    
    def get_backup_preview(self, zip_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Get preview information about a backup without restoring it.
        
        Args:
            zip_bytes: Backup ZIP file bytes
        
        Returns:
            Dictionary with backup preview information or None if invalid
        """
        try:
            is_valid, message, backup_data = self.validate_backup(zip_bytes)
            if not is_valid:
                return None
            
            # Extract preview information
            transactions = backup_data['tables']['transactions']
            
            preview = {
                "backup_date": backup_data.get('created_at', 'Unknown'),
                "format_version": backup_data.get('format_version', 'Unknown'),
                "statistics": backup_data.get('statistics', {}),
                "date_range": {
                    "earliest": None,
                    "latest": None
                },
                "categories": set(),
                "transaction_types": {}
            }
            
            # Analyze transactions
            if transactions:
                dates = [t['transaction_date'] for t in transactions]
                preview['date_range']['earliest'] = min(dates)
                preview['date_range']['latest'] = max(dates)
                
                preview['categories'] = list(set(t['category'] for t in transactions))
                
                # Count transaction types
                for txn in transactions:
                    txn_type = txn['type']
                    preview['transaction_types'][txn_type] = preview['transaction_types'].get(txn_type, 0) + 1
            
            return preview
        
        except Exception as e:
            logger.error(f"Failed to generate backup preview: {e}")
            return None


# Global instance
backup_manager = BackupManager()
