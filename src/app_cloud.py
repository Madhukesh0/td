"""
Telegram Media Downloader - Cloud Deployment Version
Multi-user support with user-provided credentials
"""
import asyncio
import os
import re
import time
import zipfile
import tempfile
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import streamlit as st
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    DocumentAttributeFilename,
    MessageMediaPhoto,
    MessageMediaDocument,
)
from telethon.tl.functions.channels import GetForumTopicsRequest
import nest_asyncio

# Allow nested event loops for Streamlit
nest_asyncio.apply()

# FFmpeg path - check multiple locations for cloud platforms
FFMPEG_PATHS = [
    "/usr/bin/ffmpeg",  # Linux default
    "/usr/local/bin/ffmpeg",  # Alternative Linux
    str(Path(__file__).parent.parent / "ffmpeg" / "ffmpeg.exe"),  # Local Windows
    "ffmpeg"  # System PATH
]

def get_ffmpeg_path():
    """Find available FFmpeg executable"""
    for path in FFMPEG_PATHS:
        if Path(path).exists() or shutil.which(path):
            return path
    return None

FFMPEG_PATH = get_ffmpeg_path()


def convert_video_to_mp4(input_path, output_path=None, delete_original=True):
    """Convert video with Opus codec to MP4 with AAC audio using FFmpeg."""
    try:
        if not FFMPEG_PATH:
            return str(input_path)
        
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = input_path.with_suffix('.mp4')
        else:
            output_path = Path(output_path)
        
        if input_path.suffix.lower() == '.mp4' and output_path == input_path:
            return str(input_path)
        
        cmd = [
            FFMPEG_PATH,
            '-i', str(input_path),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and output_path.exists():
            if delete_original and input_path != output_path and input_path.exists():
                input_path.unlink()
            return str(output_path)
        else:
            return str(input_path)
            
    except Exception as e:
        return str(input_path)


def parse_channel_url(url):
    """Parse Telegram URL to extract channel ID and optional topic ID."""
    url = url.strip()
    
    c_match = re.search(r't\.me/c/(\d+)(?:/(\d+))?', url)
    if c_match:
        channel_id = int(f"-100{c_match.group(1)}")
        topic_id = int(c_match.group(2)) if c_match.group(2) else None
        return channel_id, topic_id
    
    web_match = re.search(r'web\.telegram\.org/[^#]*#(-?\d+)', url)
    if web_match:
        return int(web_match.group(1)), None
    
    tme_match = re.search(r't\.me/([^/?]+)(?:/(\d+))?', url)
    if tme_match:
        channel = tme_match.group(1)
        topic_id = int(tme_match.group(2)) if tme_match.group(2) else None
        return channel, topic_id
    
    if url.lstrip('-').isdigit():
        return int(url), None
    
    return url, None


def format_size(size):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def format_speed(speed):
    """Format download speed"""
    return f"{format_size(speed)}/s"


def format_time(seconds):
    """Format seconds to readable time"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


async def get_client(api_id, api_hash, session_string=None, phone=None, code=None):
    """Create or connect to Telegram client with user credentials"""
    try:
        if session_string:
            client = TelegramClient(StringSession(session_string), api_id, api_hash)
        else:
            client = TelegramClient(StringSession(), api_id, api_hash)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            if phone and code:
                await client.sign_in(phone, code)
            elif phone:
                await client.send_code_request(phone)
                return client, "CODE_SENT"
            else:
                return None, "PHONE_REQUIRED"
        
        return client, "AUTHORIZED"
    except Exception as e:
        return None, f"ERROR: {str(e)}"


def get_file_info(message):
    """Extract file information from message"""
    info = {
        'name': 'unknown',
        'size': 0,
        'type': 'unknown',
        'extension': '',
        'date': message.date
    }
    
    if message.media:
        if isinstance(message.media, MessageMediaPhoto):
            info['type'] = 'photo'
            info['name'] = f"photo_{message.id}.jpg"
            info['extension'] = '.jpg'
            info['size'] = message.media.photo.sizes[-1].size if hasattr(message.media.photo.sizes[-1], 'size') else 0
        
        elif isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            info['size'] = doc.size
            
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    info['name'] = attr.file_name
                    info['extension'] = os.path.splitext(attr.file_name)[1]
            
            if doc.mime_type:
                if 'video' in doc.mime_type:
                    info['type'] = 'video'
                elif 'audio' in doc.mime_type:
                    info['type'] = 'audio'
                elif 'image' in doc.mime_type:
                    info['type'] = 'photo'
                else:
                    info['type'] = 'document'
    
    return info


async def fetch_media_list(client, channel_identifier, limit=10000, topic_id=None):
    """Fetch media messages from channel"""
    try:
        channel = await client.get_entity(channel_identifier)
        
        messages = []
        async for message in client.iter_messages(channel, limit=limit):
            if message.media:
                messages.append(message)
        
        topics_structure = {}
        topic_names = {}
        
        for msg in messages:
            topic_name = "General"
            
            if msg.reply_to and hasattr(msg.reply_to, 'reply_to_top_id') and msg.reply_to.reply_to_top_id:
                tid = msg.reply_to.reply_to_top_id
                
                if tid not in topic_names:
                    try:
                        top_msg = await client.get_messages(channel, ids=tid)
                        if top_msg and top_msg.message:
                            topic_names[tid] = top_msg.message
                        else:
                            topic_names[tid] = f"Topic {tid}"
                    except:
                        topic_names[tid] = f"Topic {tid}"
                
                topic_name = topic_names[tid]
            
            if topic_name not in topics_structure:
                topics_structure[topic_name] = []
            topics_structure[topic_name].append(msg)
        
        for topic_name in topics_structure:
            topics_structure[topic_name].sort(key=lambda m: m.date)
        
        return channel, messages, topics_structure, topic_names, topic_id
    except Exception as e:
        st.error(f"Error: {e}")
        return None, [], {}, {}, topic_id


async def download_single_file(client, channel, message, folder, file_number, file_info, progress_dict, file_id, convert_videos=True):
    """Download a single file with progress tracking"""
    try:
        original_name = file_info['name']
        
        if '.' not in original_name and file_info.get('extension'):
            original_name += file_info['extension']
        
        custom_name = f"{file_number}_{original_name}"
        custom_name = custom_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        file_path = os.path.join(folder, custom_name)
        start_time = time.time()
        
        progress_dict[file_id] = {
            'downloaded': 0,
            'total': file_info['size'],
            'speed': 0,
            'name': original_name,
            'status': 'downloading'
        }
        
        def progress_callback(current, total):
            elapsed = time.time() - start_time
            progress_dict[file_id]['downloaded'] = current
            progress_dict[file_id]['total'] = total
            progress_dict[file_id]['speed'] = current / elapsed if elapsed > 0 else 0
        
        os.makedirs(folder, exist_ok=True)
        
        downloaded_path = await message.download_media(
            file=folder,
            progress_callback=progress_callback
        )
        
        if downloaded_path and os.path.exists(downloaded_path):
            actual_ext = os.path.splitext(downloaded_path)[1]
            
            if not custom_name.endswith(actual_ext) and actual_ext:
                custom_name = os.path.splitext(custom_name)[0] + actual_ext
                file_path = os.path.join(folder, custom_name)
            
            if downloaded_path != file_path:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(downloaded_path, file_path)
                    downloaded_path = file_path
                except Exception:
                    pass
            
            elapsed = time.time() - start_time
            progress_dict[file_id]['status'] = 'completed'
            progress_dict[file_id]['time'] = elapsed
            progress_dict[file_id]['path'] = downloaded_path
            
            actual_size = os.path.getsize(downloaded_path)
            if actual_size < file_info['size'] * 0.95:
                progress_dict[file_id]['status'] = 'error'
                progress_dict[file_id]['error'] = f'Incomplete download'
                return None
            
            if convert_videos and file_info['type'] == 'video' and FFMPEG_PATH:
                progress_dict[file_id]['status'] = 'converting'
                converted_path = convert_video_to_mp4(downloaded_path)
                if converted_path:
                    downloaded_path = converted_path
                    progress_dict[file_id]['path'] = converted_path
                progress_dict[file_id]['status'] = 'completed'
            
            return downloaded_path
        else:
            progress_dict[file_id]['status'] = 'error'
            progress_dict[file_id]['error'] = 'File not saved'
            return None
    except Exception as e:
        progress_dict[file_id]['status'] = 'error'
        progress_dict[file_id]['error'] = str(e)
        return None


async def download_files(client, channel, message_ids, topic_name, progress_container, concurrent=3, convert_videos=True):
    """Download multiple files with concurrent processing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        folder = os.path.join(temp_dir, "downloads")
        
        if topic_name and topic_name != "General":
            safe_topic_name = topic_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            folder = f"{folder}/{safe_topic_name}"
        
        os.makedirs(folder, exist_ok=True)
        
        with progress_container:
            st.markdown(f"### 📥 Download Progress (⚡ {concurrent} files at once)")
            overall_progress = st.progress(0)
            overall_status = st.empty()
            speed_display = st.empty()
            active_downloads = st.empty()
            
            messages = await client.get_messages(channel, ids=message_ids)
            if not isinstance(messages, list):
                messages = [messages]
            
            download_queue = []
            for idx, message in enumerate(messages):
                if message and message.media:
                    file_info = get_file_info(message)
                    file_number = str(idx + 1).zfill(3)
                    download_queue.append((message, file_number, file_info, message.id))
            
            progress_dict = {}
            completed = 0
            downloaded_files = []
            
            for i in range(0, len(download_queue), concurrent):
                batch = download_queue[i:i+concurrent]
                
                tasks = [
                    asyncio.create_task(download_single_file(client, channel, msg, folder, file_num, file_info, progress_dict, file_id, convert_videos))
                    for msg, file_num, file_info, file_id in batch
                ]
                
                done_tasks = set()
                while len(done_tasks) < len(tasks):
                    await asyncio.sleep(0.3)
                    
                    active_files = []
                    total_speed = 0
                    
                    for file_id, progress in progress_dict.items():
                        if progress['status'] == 'downloading':
                            active_files.append(f"📄 {progress['name']}: {format_size(progress['downloaded'])} / {format_size(progress['total'])}")
                            total_speed += progress.get('speed', 0)
                        elif progress['status'] == 'converting':
                            active_files.append(f"🔄 Converting {progress['name']} to MP4...")
                    
                    if active_files:
                        active_downloads.markdown("\n\n".join(active_files[:concurrent + 2]))
                        if total_speed > 0:
                            speed_display.markdown(f"**⚡ Total Speed:** {format_speed(total_speed)}")
                        else:
                            speed_display.markdown("**🔄 Converting videos...**")
                    
                    for idx, task in enumerate(tasks):
                        if task.done() and idx not in done_tasks:
                            done_tasks.add(idx)
                            completed += 1
                            result = await task
                            if result:
                                downloaded_files.append(result)
                            overall_progress.progress(completed / len(download_queue))
                            overall_status.markdown(f"**Completed:** {completed} / {len(download_queue)} files")
                
                await asyncio.gather(*tasks)
            
            active_downloads.empty()
            speed_display.empty()
            
            successful = sum(1 for p in progress_dict.values() if p['status'] == 'completed')
            failed = sum(1 for p in progress_dict.values() if p['status'] == 'error')
            
            overall_progress.progress(1.0)
            overall_status.markdown(f"**✅ Complete:** {successful} / {len(download_queue)} files")
            
            if failed > 0:
                st.warning(f"⚠️ {failed} file(s) failed")
            
            # Create ZIP for download
            if downloaded_files:
                zip_path = os.path.join(temp_dir, "media.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in downloaded_files:
                        if os.path.exists(file_path):
                            zipf.write(file_path, os.path.basename(file_path))
                
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                st.success(f"✅ {successful} files ready!")
                st.download_button(
                    label="📦 Download ZIP",
                    data=zip_data,
                    file_name=f"telegram_media_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip"
                )


# === STREAMLIT UI ===

st.set_page_config(
    page_title="Telegram Media Downloader",
    page_icon="📥",
    layout="wide"
)

st.title("📥 Telegram Media Downloader")
st.markdown("Download media from Telegram channels - **Free Cloud Version**")

# Initialize session state
if 'client' not in st.session_state:
    st.session_state.client = None
if 'session_string' not in st.session_state:
    st.session_state.session_string = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'media_list' not in st.session_state:
    st.session_state.media_list = []
if 'channel_info' not in st.session_state:
    st.session_state.channel_info = None

# Sidebar - Authentication
with st.sidebar:
    st.header("🔐 Authentication")
    
    if not st.session_state.authenticated:
        st.info("📱 You need your own Telegram API credentials. Get them from: https://my.telegram.org/apps")
        
        with st.expander("ℹ️ How to get API credentials", expanded=False):
            st.markdown("""
            1. Go to https://my.telegram.org/apps
            2. Log in with your phone number
            3. Create a new application
            4. Copy **API ID** and **API Hash**
            5. Paste them below
            """)
        
        api_id = st.text_input("API ID", type="password")
        api_hash = st.text_input("API Hash", type="password")
        
        # Session string for returning users
        session_string = st.text_area("Session String (optional - for returning users)", height=100)
        
        if api_id and api_hash:
            if session_string:
                if st.button("🔓 Connect with Session"):
                    with st.spinner("Connecting..."):
                        client, status = asyncio.run(get_client(int(api_id), api_hash, session_string))
                        if status == "AUTHORIZED":
                            st.session_state.client = client
                            st.session_state.authenticated = True
                            st.session_state.api_id = int(api_id)
                            st.session_state.api_hash = api_hash
                            st.success("✅ Connected!")
                            st.rerun()
                        else:
                            st.error(f"❌ {status}")
            else:
                phone = st.text_input("Phone Number (with country code, e.g., +1234567890)")
                
                if phone and 'code_sent' not in st.session_state:
                    if st.button("📱 Send Code"):
                        with st.spinner("Sending code..."):
                            client, status = asyncio.run(get_client(int(api_id), api_hash, None, phone))
                            if status == "CODE_SENT":
                                st.session_state.temp_client = client
                                st.session_state.code_sent = True
                                st.session_state.phone = phone
                                st.session_state.api_id = int(api_id)
                                st.session_state.api_hash = api_hash
                                st.success("✅ Code sent to Telegram!")
                                st.rerun()
                            else:
                                st.error(f"❌ {status}")
                
                if st.session_state.get('code_sent'):
                    code = st.text_input("Verification Code")
                    if code and st.button("✅ Verify"):
                        with st.spinner("Verifying..."):
                            try:
                                client = st.session_state.temp_client
                                asyncio.run(client.sign_in(st.session_state.phone, code))
                                
                                # Save session string
                                session_str = client.session.save()
                                
                                st.session_state.client = client
                                st.session_state.session_string = session_str
                                st.session_state.authenticated = True
                                
                                st.success("✅ Authenticated!")
                                st.info(f"💾 Save this session string for next time:")
                                st.code(session_str)
                                
                                del st.session_state.code_sent
                                del st.session_state.temp_client
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
    else:
        st.success("✅ Authenticated")
        if st.button("🚪 Logout"):
            if st.session_state.client:
                asyncio.run(st.session_state.client.disconnect())
            st.session_state.clear()
            st.rerun()
        
        st.markdown("---")
        st.subheader("📥 Download Settings")
        
        channel_url = st.text_input(
            "Channel URL/ID",
            placeholder="https://t.me/channelname",
            help="Enter Telegram channel URL"
        )
        
        fetch_limit = st.slider("Messages to fetch", 100, 5000, 1000, 100)
        concurrent_downloads = st.slider("Concurrent downloads", 1, 5, 2, 1)
        
        st.markdown("---")
        st.subheader("🎬 Video Settings")
        convert_videos = st.checkbox("Auto-convert to MP4", value=bool(FFMPEG_PATH))
        
        if not FFMPEG_PATH:
            st.warning("⚠️ FFmpeg not available - videos may not play properly")
        
        fetch_button = st.button("🔍 Fetch Media", type="primary")

# Main content
if st.session_state.authenticated:
    if fetch_button and channel_url:
        with st.spinner("Fetching media..."):
            channel_id, topic_id = parse_channel_url(channel_url)
            
            channel, messages, topics_structure, topic_names, _ = asyncio.run(
                fetch_media_list(st.session_state.client, channel_id, fetch_limit, topic_id)
            )
            
            if channel:
                st.session_state.channel_info = {"title": channel.title, "id": channel.id}
                st.session_state.media_list = [get_file_info(msg) for msg in messages]
                st.session_state.messages_map = {msg.id: msg for msg in messages}
                st.session_state.topics_structure = topics_structure
                
                st.success(f"✅ Fetched {len(messages)} media files from **{channel.title}**")
    
    # Display media
    if st.session_state.media_list:
        st.markdown("---")
        st.subheader(f"📂 {st.session_state.channel_info['title']}")
        
        # Topic selector
        topics = list(st.session_state.topics_structure.keys())
        selected_topic = st.selectbox("Select Topic/Folder", ["All"] + topics)
        
        # Filter media
        if selected_topic == "All":
            display_messages = [msg for msgs in st.session_state.topics_structure.values() for msg in msgs]
        else:
            display_messages = st.session_state.topics_structure[selected_topic]
        
        st.info(f"📊 {len(display_messages)} files")
        
        # Media list
        selected_ids = []
        for idx, msg in enumerate(display_messages[:50]):  # Show first 50
            file_info = get_file_info(msg)
            col1, col2, col3, col4 = st.columns([1, 6, 3, 2])
            
            with col1:
                if st.checkbox("Select", key=f"sel_{msg.id}"):
                    selected_ids.append(msg.id)
            with col2:
                st.text(file_info['name'])
            with col3:
                st.text(f"{file_info['type']} - {format_size(file_info['size'])}")
            with col4:
                st.text(msg.date.strftime("%Y-%m-%d"))
        
        # Bulk actions
        if selected_ids:
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info(f"Selected: {len(selected_ids)} files")
            with col2:
                if st.button("📥 Download Selected", type="primary"):
                    progress_container = st.container()
                    asyncio.run(download_files(
                        st.session_state.client,
                        st.session_state.channel_info['id'],
                        selected_ids,
                        selected_topic if selected_topic != "All" else None,
                        progress_container,
                        concurrent_downloads,
                        convert_videos
                    ))

else:
    st.info("👈 Please authenticate using the sidebar to start downloading media")
    
    st.markdown("---")
    st.markdown("""
    ### Features:
    - 📥 Download photos, videos, and documents
    - 🎬 Auto-convert videos to MP4 (if FFmpeg available)
    - ⚡ Concurrent downloads for speed
    - 📦 Download as ZIP file
    - 🔐 Secure - uses your own API credentials
    - 💾 Session string for quick re-login
    
    ### Privacy:
    - Your credentials are never stored on the server
    - All downloads are temporary (deleted after ZIP creation)
    - Session strings are stored only in your browser
    """)
