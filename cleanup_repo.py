#!/usr/bin/env python3
"""
Repository Cleanup Script
Removes files that shouldn't be committed to git.
Run this before your first git commit.
"""

import os
import shutil
import sys
from pathlib import Path

def remove_directory(path: str, description: str):
    """Remove a directory if it exists."""
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"✅ Removed {description}: {path}")
            return True
        except Exception as e:
            print(f"❌ Failed to remove {path}: {e}")
            return False
    else:
        print(f"ℹ️  {description} not found: {path}")
        return True

def remove_file(path: str, description: str):
    """Remove a file if it exists."""
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"✅ Removed {description}: {path}")
            return True
        except Exception as e:
            print(f"❌ Failed to remove {path}: {e}")
            return False
    else:
        print(f"ℹ️  {description} not found: {path}")
        return True

def remove_pycache():
    """Remove all __pycache__ directories."""
    removed = 0
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(cache_dir)
                removed += 1
            except Exception as e:
                print(f"⚠️  Could not remove {cache_dir}: {e}")
    print(f"✅ Removed {removed} __pycache__ directories")
    return removed

def remove_receipt_images():
    """Remove generated receipt images but keep directory."""
    receipts_dir = Path("app/receipts/output")
    if receipts_dir.exists():
        removed = 0
        for file in receipts_dir.glob("*.jpg"):
            file.unlink()
            removed += 1
        for file in receipts_dir.glob("*.png"):
            file.unlink()
            removed += 1
        for file in receipts_dir.glob("*.jpeg"):
            file.unlink()
            removed += 1
        print(f"✅ Removed {removed} receipt image files")
        return removed
    return 0

def remove_log_files():
    """Remove log files."""
    logs_dir = Path("logs")
    if logs_dir.exists():
        removed = 0
        for file in logs_dir.glob("*.log"):
            file.unlink()
            removed += 1
        for file in logs_dir.glob("*.zip"):
            file.unlink()
            removed += 1
        print(f"✅ Removed {removed} log files")
        return removed
    return 0

def main():
    """Main cleanup function."""
    print("=" * 60)
    print("🧹 Repository Cleanup Script")
    print("=" * 60)
    print()
    print("This script will remove files that shouldn't be in git:")
    print("  - venv/ (virtual environment)")
    print("  - __pycache__/ (Python cache)")
    print("  - .env (environment variables)")
    print("  - logs/*.log (log files)")
    print("  - app/receipts/output/*.jpg, *.png (generated receipts)")
    print()
    
    response = input("Continue? (y/n): ").lower().strip()
    if response != 'y':
        print("❌ Cleanup cancelled")
        sys.exit(0)
    
    print()
    print("Starting cleanup...")
    print()
    
    # Remove virtual environment
    remove_directory("venv", "Virtual environment")
    
    # Remove __pycache__ directories
    remove_pycache()
    
    # Remove .env file
    remove_file(".env", "Environment file")
    
    # Remove log files
    remove_log_files()
    
    # Remove receipt images
    remove_receipt_images()
    
    # Remove database files
    remove_file("paystack_app.db", "SQLite database")
    remove_file("*.db", "Database files")
    
    print()
    print("=" * 60)
    print("✅ Cleanup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Review the changes")
    print("  2. Initialize git: git init")
    print("  3. Add files: git add .")
    print("  4. Commit: git commit -m 'Initial commit'")
    print()

if __name__ == "__main__":
    main()

