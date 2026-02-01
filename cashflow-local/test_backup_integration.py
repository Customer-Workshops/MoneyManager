"""
Integration test to verify backup/restore functionality works end-to-end
"""
import sys
import os
import tempfile
import shutil

# Create temporary directory for test database
test_dir = tempfile.mkdtemp()
test_db_path = os.path.join(test_dir, 'test_integration.duckdb')

# Set test DB path
os.environ['DB_PATH'] = test_db_path

from src.backup import backup_manager
from src.database import db_manager

def test_end_to_end():
    """Test complete backup and restore workflow"""
    print("🧪 Starting end-to-end backup/restore test...")
    print(f"📁 Using test database: {test_db_path}")
    
    try:
        # 1. Add some test data
        print("\n1️⃣ Adding test data...")
        test_transactions = [
            {
                'hash': 'integration_test_1',
                'transaction_date': '2024-01-15',
                'description': 'Test Purchase',
                'amount': 100.00,
                'type': 'Debit',
                'category': 'Shopping',
                'source_file_hash': 'test_file'
            }
        ]
        db_manager.execute_insert('transactions', test_transactions)
        count = db_manager.execute_query("SELECT COUNT(*) FROM transactions")[0][0]
        print(f"   ✅ Added {count} transaction(s)")
        
        # 2. Create backup
        print("\n2️⃣ Creating backup...")
        zip_bytes, metadata = backup_manager.create_backup()
        print(f"   ✅ Backup created: {len(zip_bytes)} bytes")
        print(f"   📊 Stats: {metadata['statistics']}")
        
        # 3. Validate backup
        print("\n3️⃣ Validating backup...")
        is_valid, message, backup_data = backup_manager.validate_backup(zip_bytes)
        print(f"   {'✅' if is_valid else '❌'} {message}")
        
        # 4. Get preview
        print("\n4️⃣ Getting backup preview...")
        preview = backup_manager.get_backup_preview(zip_bytes)
        if preview:
            print(f"   ✅ Preview generated")
            print(f"   📅 Date range: {preview['date_range']['earliest']} to {preview['date_range']['latest']}")
            print(f"   📊 Statistics: {preview['statistics']}")
        
        # 5. Clear database
        print("\n5️⃣ Clearing database...")
        with db_manager.get_connection() as conn:
            conn.execute("DELETE FROM transactions")
        count = db_manager.execute_query("SELECT COUNT(*) FROM transactions")[0][0]
        print(f"   ✅ Database cleared (count: {count})")
        
        # 6. Restore from backup
        print("\n6️⃣ Restoring from backup (full mode)...")
        success, message, stats = backup_manager.restore_backup(zip_bytes, mode="full")
        print(f"   {'✅' if success else '❌'} {message}")
        print(f"   📊 Restore stats: {stats}")
        
        # 7. Verify restoration
        print("\n7️⃣ Verifying restoration...")
        count = db_manager.execute_query("SELECT COUNT(*) FROM transactions")[0][0]
        print(f"   ✅ Transactions restored: {count}")
        
        print("\n✅ All tests passed! Backup/restore is working correctly.\n")
    
    finally:
        # Cleanup
        print("🧹 Cleaning up temporary test directory...")
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        print(f"   ✅ Removed: {test_dir}\n")

if __name__ == "__main__":
    try:
        test_end_to_end()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        # Cleanup on error
        if 'test_dir' in locals() and os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        sys.exit(1)
