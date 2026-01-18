import os
import glob
import time

print("=" * 60)
print("Telegram Session Cleanup Utility")
print("=" * 60)

# Get all session files
session_files = glob.glob("*.session*")

if not session_files:
    print("\n✅ No session files found.")
    exit(0)

print(f"\n📁 Found {len(session_files)} session-related file(s):\n")

# List all files
for idx, file in enumerate(session_files, 1):
    file_size = os.path.getsize(file)
    file_time = time.ctime(os.path.getmtime(file))
    print(f"{idx}. {file}")
    print(f"   Size: {file_size} bytes")
    print(f"   Modified: {file_time}")
    print()

# Check for journal files (indicates active session)
journal_files = [f for f in session_files if f.endswith('-journal')]

if journal_files:
    print("⚠️  WARNING: Found active session journal files:")
    for jf in journal_files:
        print(f"   - {jf}")
    print("\n   These indicate a session is currently active or was not closed properly.")
    print("   It's safe to delete journal files if no Telegram apps are running.\n")

# Ask user what to do
print("-" * 60)
print("Options:")
print("1. Delete ALL session files (you'll need to re-authenticate)")
print("2. Delete only journal files (may fix lock issues)")
print("3. Keep everything and exit")
print("-" * 60)

choice = input("\nEnter your choice (1/2/3): ").strip()

if choice == "1":
    print("\n🗑️  Deleting all session files...")
    for file in session_files:
        try:
            os.remove(file)
            print(f"   ✓ Deleted: {file}")
        except Exception as e:
            print(f"   ✗ Failed to delete {file}: {e}")
    print("\n✅ Done! You'll need to run 'python authenticate.py' again.")

elif choice == "2":
    if journal_files:
        print("\n🗑️  Deleting journal files...")
        for file in journal_files:
            try:
                os.remove(file)
                print(f"   ✓ Deleted: {file}")
            except Exception as e:
                print(f"   ✗ Failed to delete {file}: {e}")
        print("\n✅ Done! Try running the Streamlit app again.")
    else:
        print("\n✅ No journal files to delete.")

elif choice == "3":
    print("\n✅ No changes made. Exiting.")

else:
    print("\n❌ Invalid choice. Exiting.")

print("\n" + "=" * 60)
