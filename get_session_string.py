"""
Generate a SESSION_STRING for cloud deployment.
Run this locally to get your session string for Streamlit Cloud secrets.
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
import os

# Load credentials from .env
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

print("=" * 60)
print("TELEGRAM SESSION STRING GENERATOR")
print("=" * 60)
print("\nThis will generate a SESSION_STRING for cloud deployment.")
print("You'll need to log in with your phone number and verification code.\n")

# Create client with empty string session
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n✅ Successfully authenticated!")
    print("\n" + "=" * 60)
    print("YOUR SESSION_STRING (copy this):")
    print("=" * 60)
    session_string = client.session.save()
    print(session_string)
    print("=" * 60)
    print("\n📋 NEXT STEPS:")
    print("1. Copy the SESSION_STRING above")
    print("2. Go to your Streamlit Cloud app settings")
    print("3. Navigate to: Secrets > Edit")
    print("4. Add this to your secrets.toml:")
    print("\n" + "─" * 60)
    print(f'API_ID = "{api_id}"')
    print(f'API_HASH = "{api_hash}"')
    print(f'SESSION_STRING = "{session_string}"')
    print(f'SESSION_NAME = "cloud_session"')
    print("─" * 60)
    print("\n✅ Save the secrets and your app will work on Streamlit Cloud!")
