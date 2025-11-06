"""Test database path resolution"""
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
db_path = os.path.join(parent_dir, 'Diary', 'instance', 'diary.db')
db_path = os.path.abspath(db_path)

print("\n" + "="*60)
print("DATABASE PATH TEST")
print("="*60)
print(f"Current dir: {current_dir}")
print(f"Parent dir: {parent_dir}")
print(f"Database path: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")
print("="*60 + "\n")

if os.path.exists(db_path):
    size = os.path.getsize(db_path) / 1024
    print(f"✓ Database found! Size: {size:.2f} KB")
else:
    print("✗ Database NOT found at this location")
    print("\nExpected location:")
    print(db_path)

