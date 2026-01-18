"""
Simple authentication script for local Telegram session
"""
import os
from telethon.sync import TelegramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME", "session")

print("🔐 Telegram Authentication")
print("=" * 40)

# Create client
client = TelegramClient(session_name, api_id, api_hash)

# Connect and authenticate
client.start()

# Get user info
me = client.get_me()
print(f"\n✅ Successfully authenticated!")
print(f"👤 Name: {me.first_name} {me.last_name or ''}")
print(f"📱 Phone: {me.phone}")
print(f"💾 Session file: {session_name}.session")
print("\n✨ You can now run the Streamlit app!")

client.disconnect()
