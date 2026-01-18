import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient

# Load environment variables
load_dotenv()

# Retrieve values from .env
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME", "default_session")

print("=" * 50)
print("Telegram Authentication")
print("=" * 50)

# Create and start the client
with TelegramClient(session_name, api_id, api_hash) as client:
    print("\n✅ Successfully authenticated!")
    print(f"Session file created: {session_name}.session")
    print("\nYou can now use the Streamlit app!")
    print("Run: streamlit run src/app.py")
