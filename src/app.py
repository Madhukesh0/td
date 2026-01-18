import asyncio
import os
import re
import time
import zipfile
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
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

# Load environment variables
load_dotenv()

# Retrieve values from .env
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME", "default_session")


# Global client instance to avoid database locks
_client_instance = None
_client_lock = asyncio.Lock()

# FFmpeg path
FFMPEG_PATH = str(Path(__file__).parent.parent / "ffmpeg" / "ffmpeg.exe")


def convert_video_to_mp4(input_path, output_path=None, delete_original=True):
    """Convert video with Opus codec to MP4 with AAC audio using FFmpeg.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output MP4 file (optional, will auto-generate)
        delete_original: Whether to delete the original file after conversion
    
    Returns:
        Path to converted file or None if conversion failed
    """
    try:
        input_path = Path(input_path)
        
        # Check if FFmpeg exists
        if not Path(FFMPEG_PATH).exists():
            print(f"⚠️ FFmpeg not found at {FFMPEG_PATH}")
            return str(input_path)
        
        # Generate output path if not provided
        if output_path is None:
            output_path = input_path.with_suffix('.mp4')
        else:
            output_path = Path(output_path)
        
        # Skip if already MP4 with no opus codec
        if input_path.suffix.lower() == '.mp4' and output_path == input_path:
            return str(input_path)
        
        print(f"🔄 Converting {input_path.name} to MP4...")
        
        # FFmpeg command to convert video
        # -c:v copy: Copy video codec (no re-encoding for speed)
        # -c:a aac: Convert audio to AAC codec
        # -b:a 192k: Audio bitrate 192 kbps
        # -y: Overwrite output file without asking
        cmd = [
            str(FFMPEG_PATH),
            '-i', str(input_path),
            '-c:v', 'copy',  # Copy video stream
            '-c:a', 'aac',   # Convert audio to AAC
            '-b:a', '192k',  # Audio bitrate
            '-movflags', '+faststart',  # Optimize for streaming
            '-y',  # Overwrite
            str(output_path)
        ]
        
        # Run FFmpeg with suppressed output
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0 and output_path.exists():
            print(f"✅ Converted to MP4: {output_path.name}")
            
            # Delete original if requested and different from output
            if delete_original and input_path != output_path and input_path.exists():
                input_path.unlink()
                print(f"🗑️ Deleted original: {input_path.name}")
            
            return str(output_path)
        else:
            print(f"❌ Conversion failed: {result.stderr[:200]}")
            return str(input_path)  # Return original if conversion failed
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ Conversion timeout for {input_path.name}")
        return str(input_path)
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return str(input_path)


def parse_channel_url(url):
    """Parse Telegram URL to extract channel ID and optional topic ID.
    Supports:
    - https://t.me/c/2381311281/21 (private channel with topic ID 21)
    - https://web.telegram.org/a/#-1002381311281
    - https://t.me/channelname
    - Direct IDs: -1002381311281
    
    Returns: (channel_id, topic_id)
    """
    url = url.strip()
    
    # Handle t.me/c/ format (private channels) with optional topic ID
    c_match = re.search(r't\.me/c/(\d+)(?:/(\d+))?', url)
    if c_match:
        # Convert to full channel ID format
        channel_id = int(f"-100{c_match.group(1)}")
        topic_id = int(c_match.group(2)) if c_match.group(2) else None
        return channel_id, topic_id
    
    # Handle web.telegram.org URLs
    web_match = re.search(r'web\.telegram\.org/[^#]*#(-?\d+)', url)
    if web_match:
        return int(web_match.group(1)), None
    
    # Handle regular t.me links with optional message/topic
    tme_match = re.search(r't\.me/([^/?]+)(?:/(\d+))?', url)
    if tme_match:
        channel = tme_match.group(1)
        topic_id = int(tme_match.group(2)) if tme_match.group(2) else None
        return channel, topic_id
    
    # Handle direct channel IDs
    if re.match(r'^-?\d+$', url):
        return int(url), None
    
    # Return as username
    return url.lstrip('@'), None


def get_file_info(message):
    """Extract file information from a message."""
    info = {
        "id": message.id,
        "date": message.date.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "Unknown",
        "name": f"file_{message.id}",
        "size": 0,
        "mime_type": "",
        "extension": ""
    }
    
    if message.photo:
        info["type"] = "Photo"
        info["extension"] = ".jpg"
        info["name"] = f"photo_{message.id}.jpg"
        if hasattr(message.photo, 'sizes') and message.photo.sizes:
            info["size"] = max(size.size if hasattr(size, 'size') else 0 
                             for size in message.photo.sizes)
    elif message.document:
        info["type"] = "Document"
        info["size"] = message.document.size
        info["mime_type"] = message.document.mime_type or "unknown"
        
        # Get filename and extension from attributes
        for attr in message.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                info["name"] = attr.file_name
                # Extract extension
                if '.' in attr.file_name:
                    info["extension"] = os.path.splitext(attr.file_name)[1]
                break
        
        # If no filename found, generate one based on mime type
        if info["name"] == f"file_{message.id}":
            ext = ""
            if "video" in info["mime_type"]:
                ext = ".mp4"
                info["type"] = "Video"
            elif "audio" in info["mime_type"]:
                ext = ".mp3"
                info["type"] = "Audio"
            elif "application/pdf" in info["mime_type"]:
                ext = ".pdf"
                info["type"] = "PDF"
            elif "application/zip" in info["mime_type"]:
                ext = ".zip"
                info["type"] = "ZIP"
            info["name"] = f"document_{message.id}{ext}"
            info["extension"] = ext
        
        # Determine document type based on mime or extension
        if "video" in info["mime_type"] or info["extension"] in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            info["type"] = "Video"
        elif "audio" in info["mime_type"] or info["extension"] in ['.mp3', '.m4a', '.wav', '.ogg']:
            info["type"] = "Audio"
        elif "application/pdf" in info["mime_type"] or info["extension"] == '.pdf':
            info["type"] = "PDF"
        elif "application/zip" in info["mime_type"] or info["extension"] == '.zip':
            info["type"] = "ZIP"
    elif message.video:
        info["type"] = "Video"
        info["extension"] = ".mp4"
        info["name"] = f"video_{message.id}.mp4"
        info["size"] = message.video.size if hasattr(message.video, 'size') else 0
    
    return info


def format_size(size):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


async def get_client():
    """Get or create a shared Telegram client to avoid database locks."""
    global _client_instance
    
    # Use existing client if available and connected
    if _client_instance and _client_instance.is_connected():
        return _client_instance
    
    async with _client_lock:
        # Double-check after acquiring lock
        if _client_instance and _client_instance.is_connected():
            return _client_instance
        
        try:
            # Close any existing disconnected client
            if _client_instance:
                try:
                    await _client_instance.disconnect()
                except:
                    pass
            
            # Try to load session string from SQLite session
            session_file = f"{session_name}.session"
            session_to_use = session_name
            
            # If SQLite session is locked, convert to StringSession
            if os.path.exists(session_file):
                try:
                    # Try to read the session with a short timeout
                    temp_client = TelegramClient(session_name, api_id, api_hash)
                    await asyncio.wait_for(temp_client.connect(), timeout=3)
                    
                    if await temp_client.is_user_authorized():
                        # Export to string session to avoid locks
                        string_session = StringSession.save(temp_client.session)
                        await temp_client.disconnect()
                        session_to_use = StringSession(string_session)
                        st.info("✅ Using in-memory session to avoid database locks")
                    else:
                        await temp_client.disconnect()
                        st.error("Please authorize the client first by running: python authenticate.py")
                        return None
                        
                except (asyncio.TimeoutError, Exception) as e:
                    # Session is locked, try to use it anyway with retry
                    st.warning("⚠️ Session file locked, retrying...")
                    await asyncio.sleep(1)
                    
                    # Retry with the file session
                    try:
                        session_to_use = session_name
                    except:
                        st.error(f"Cannot access session file: {e}")
                        st.info("💡 Tip: Close any other programs using Telegram (including authenticate.py)")
                        return None
            else:
                st.error("Session file not found. Please run: python authenticate.py")
                return None
            
            # Create new client with the selected session
            client = TelegramClient(
                session_to_use, 
                api_id, 
                api_hash,
                connection_retries=5,
                retry_delay=1,
                auto_reconnect=True,
                sequential_updates=True,
                timeout=30
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                st.error("Please authorize the client first by running: python authenticate.py")
                return None
            
            _client_instance = client
            return client
            
        except Exception as e:
            st.error(f"Error connecting to Telegram: {e}")
            st.info("💡 Try: \n1. Close other Telegram apps\n2. Re-run: python authenticate.py\n3. Restart Streamlit")
            return None


async def get_channel_info(channel_identifier):
    """Get channel information and check if it has topics/forums."""
    client = await get_client()
    if not client:
        return None, None
    
    try:
        channel = await client.get_entity(channel_identifier)
        
        # Check if channel has topics/forums enabled
        has_topics = hasattr(channel, 'forum') and channel.forum
        topics = []
        
        if has_topics:
            # Fetch all topics/folders
            async for dialog in client.iter_dialogs():
                if hasattr(dialog.entity, 'id') and dialog.entity.id == channel.id:
                    # This is a forum channel
                    result = await client(GetForumTopicsRequest(
                        channel=channel,
                        offset_date=None,
                        offset_id=0,
                        offset_topic=0,
                        limit=100
                    ))
                    for topic in result.topics:
                        topics.append({
                            'id': topic.id,
                            'title': topic.title,
                            'icon_emoji_id': getattr(topic, 'icon_emoji_id', None)
                        })
                    break
        
        # Don't disconnect - using shared client
        return channel, topics
    except Exception as e:
        st.error(f"Error fetching channel info: {e}")
        return None, None


async def fetch_media_list(channel_identifier, limit=10000, topic_id=None):
    """Fetch all media from a channel or specific topic with proper folder structure.
    
    Args:
        channel_identifier: Channel username or ID
        limit: Maximum messages to fetch
        topic_id: Specific topic/thread ID to fetch from (optional)
    """
    client = await get_client()
    if not client:
        return None, [], {}, {}, topic_id
    
    try:
        channel = await client.get_entity(channel_identifier)
        
        # Check if it's a forum/topic-based channel
        is_forum = hasattr(channel, 'forum') and channel.forum
        
        # Fetch messages - either from specific topic or all
        if topic_id:
            # Fetch messages from specific topic only
            messages = await client.get_messages(channel, limit=limit, reply_to=topic_id)
        else:
            # Fetch all messages
            messages = await client.get_messages(channel, limit=limit)
        
        # Filter only messages with media
        media_messages = [msg for msg in messages if msg.media]
        
        # Organize messages by topic/thread with proper names
        topics_structure = {}
        topic_names = {}  # Map topic_id to topic name
        
        # First pass: identify topics and their names
        for msg in messages:
            if msg.reply_to and hasattr(msg.reply_to, 'reply_to_top_id'):
                topic_id = msg.reply_to.reply_to_top_id
                if topic_id not in topic_names:
                    # Try to get the topic message to extract the name
                    try:
                        topic_msg = await client.get_messages(channel, ids=topic_id)
                        if topic_msg and topic_msg.message:
                            # Use first line of message as topic name, or full message if short
                            topic_title = topic_msg.message.split('\n')[0][:50]
                            topic_names[topic_id] = topic_title
                        else:
                            topic_names[topic_id] = f"Topic_{topic_id}"
                    except:
                        topic_names[topic_id] = f"Topic_{topic_id}"
        
        # Second pass: organize media by topic
        for msg in media_messages:
            if msg.reply_to and hasattr(msg.reply_to, 'reply_to_top_id'):
                topic_id = msg.reply_to.reply_to_top_id
                topic_name = topic_names.get(topic_id, f"Topic_{topic_id}")
            else:
                topic_name = "General"
            
            if topic_name not in topics_structure:
                topics_structure[topic_name] = []
            topics_structure[topic_name].append(msg)
        
        # Sort messages in each topic by date (oldest first to maintain order)
        for topic_name in topics_structure:
            topics_structure[topic_name].sort(key=lambda m: m.date)
        
        # Don't disconnect - using shared client
        return channel, media_messages, topics_structure, topic_names, topic_id
    except Exception as e:
        st.error(f"Error: {e}")
        return None, [], {}, {}, topic_id


async def download_single_file(client, channel, message, folder, file_number, file_info, progress_dict, file_id):
    """Download a single file with progress tracking."""
    try:
        # Preserve original filename with proper extension
        original_name = file_info['name']
        
        # Ensure filename has proper extension
        if '.' not in original_name and file_info.get('extension'):
            original_name += file_info['extension']
        
        # Add number prefix for ordering
        custom_name = f"{file_number}_{original_name}"
        
        # Sanitize filename to remove invalid characters
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
        
        # Ensure folder exists
        os.makedirs(folder, exist_ok=True)
        
        # Download file - let Telegram handle the extension automatically
        # If we don't specify extension, Telethon will preserve the original
        downloaded_path = await message.download_media(
            file=folder,  # Just specify folder, let Telethon name it
            progress_callback=progress_callback
        )
        
        # Rename to our custom name with number prefix
        if downloaded_path and os.path.exists(downloaded_path):
            # Get the extension from the downloaded file
            actual_ext = os.path.splitext(downloaded_path)[1]
            
            # If our custom name doesn't have this extension, add it
            if not custom_name.endswith(actual_ext) and actual_ext:
                custom_name = os.path.splitext(custom_name)[0] + actual_ext
                file_path = os.path.join(folder, custom_name)
            
            # Rename to numbered version
            if downloaded_path != file_path:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(downloaded_path, file_path)
                    downloaded_path = file_path
                except Exception as rename_error:
                    # If rename fails, keep original name
                    st.warning(f"Could not rename {os.path.basename(downloaded_path)}: {rename_error}")
            
            elapsed = time.time() - start_time
            progress_dict[file_id]['status'] = 'completed'
            progress_dict[file_id]['time'] = elapsed
            progress_dict[file_id]['path'] = downloaded_path
            
            # Verify file size matches
            actual_size = os.path.getsize(downloaded_path)
            if actual_size < file_info['size'] * 0.95:  # Allow 5% tolerance
                progress_dict[file_id]['status'] = 'error'
                progress_dict[file_id]['error'] = f'Incomplete download: {format_size(actual_size)} / {format_size(file_info["size"])}'
                return None
            
            # Convert video if enabled and it's a video file
            if st.session_state.get('convert_videos', True) and file_info['type'] == 'video':
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


async def download_files(channel_identifier, message_ids, progress_container, topic_name=None, concurrent=3):
    """Download selected files organized by topic folders with detailed progress."""
    client = await get_client()
    if not client:
        return
    
    try:
        channel = await client.get_entity(channel_identifier)
        
        # Create base downloads folder
        base_folder = f"downloads/{channel.title.replace(' ', '_').replace('/', '_')}"
        
        # If topic specified, create subfolder
        if topic_name and topic_name != "General":
            # Sanitize folder name
            safe_topic_name = topic_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            folder = f"{base_folder}/{safe_topic_name}"
        else:
            folder = base_folder
        
        os.makedirs(folder, exist_ok=True)
        
        total = len(message_ids)
        
        # Create progress UI elements
        with progress_container:
            st.markdown(f"### 📥 Download Progress (⚡ {concurrent} files at once)")
            overall_progress = st.progress(0)
            overall_status = st.empty()
            
            speed_display = st.empty()
            active_downloads = st.empty()
            
            # Get all messages first
            messages = await client.get_messages(channel, ids=message_ids)
            if not isinstance(messages, list):
                messages = [messages]
            
            # Filter out messages without media
            download_queue = []
            for idx, message in enumerate(messages):
                if message and message.media:
                    file_info = get_file_info(message)
                    file_number = str(idx + 1).zfill(3)
                    download_queue.append((message, file_number, file_info, message.id))
            
            progress_dict = {}
            completed = 0
            
            # Download in batches for concurrent processing
            for i in range(0, len(download_queue), concurrent):
                batch = download_queue[i:i+concurrent]
                
                # Start concurrent downloads - create tasks properly
                tasks = [
                    asyncio.create_task(download_single_file(client, channel, msg, folder, file_num, file_info, progress_dict, file_id))
                    for msg, file_num, file_info, file_id in batch
                ]
                
                # Monitor progress while downloading
                done_tasks = set()
                while len(done_tasks) < len(tasks):
                    await asyncio.sleep(0.3)
                    
                    # Update UI
                    active_files = []
                    total_speed = 0
                    
                    for file_id, progress in progress_dict.items():
                        if progress['status'] == 'downloading':
                            active_files.append(f"📄 {progress['name']}: {format_size(progress['downloaded'])} / {format_size(progress['total'])}")
                            total_speed += progress.get('speed', 0)
                        elif progress['status'] == 'converting':
                            active_files.append(f"🔄 Converting {progress['name']} to MP4...")
                    
                    if active_files:
                        active_downloads.markdown("\n\n".join(active_files[:concurrent + 2]))  # Show a bit more for converting files
                        if total_speed > 0:
                            speed_display.markdown(f"**⚡ Total Speed:** {format_speed(total_speed)}")
                        else:
                            speed_display.markdown("**🔄 Converting videos...**")
                    
                    # Check completed tasks
                    for idx, task in enumerate(tasks):
                        if task.done() and idx not in done_tasks:
                            done_tasks.add(idx)
                            completed += 1
                            overall_progress.progress(completed / len(download_queue))
                            overall_status.markdown(f"**Completed:** {completed} / {len(download_queue)} files")
                
                # Wait for all tasks in batch to complete
                await asyncio.gather(*tasks)
            
            # Clear active downloads display
            active_downloads.empty()
            speed_display.empty()
            
            # Show summary
            successful = sum(1 for p in progress_dict.values() if p['status'] == 'completed')
            failed = sum(1 for p in progress_dict.values() if p['status'] == 'error')
            total_time = sum(p.get('time', 0) for p in progress_dict.values() if 'time' in p)
            avg_time = total_time / successful if successful > 0 else 0
                
            overall_progress.progress(1.0)
            overall_status.markdown(f"**✅ Complete:** {successful} / {len(download_queue)} files successfully downloaded")
            
            if failed > 0:
                st.warning(f"⚠️ {failed} file(s) failed to download")
                with st.expander("View failed files"):
                    for file_id, p in progress_dict.items():
                        if p['status'] == 'error':
                            st.text(f"❌ {p['name']}: {p.get('error', 'Unknown error')}")
            
            if avg_time > 0:
                st.info(f"⚡ Average time per file: {format_time(avg_time)}")
            
            if successful > 0:
                st.success(f"✅ Successfully downloaded {successful} files to `{folder}/`")
                
                # List downloaded files
                with st.expander("📁 View downloaded files"):
                    for p in progress_dict.values():
                        if p['status'] == 'completed' and 'path' in p:
                            st.text(f"✓ {os.path.basename(p['path'])}")
                
                st.balloons()
        
        # Don't disconnect - using shared client
        # Session will save automatically
    except Exception as e:
        st.error(f"Download error: {e}")


def format_speed(bytes_per_second):
    """Format speed in bytes/second to human-readable format."""
    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
        if bytes_per_second < 1024.0:
            return f"{bytes_per_second:.2f} {unit}"
        bytes_per_second /= 1024.0
    return f"{bytes_per_second:.2f} TB/s"


def format_time(seconds):
    """Format seconds to human-readable time."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


async def export_as_zip(channel_identifier, message_ids, zip_name, progress_container, topic_name=None):
    """Download selected files and create a ZIP archive."""
    client = await get_client()
    if not client:
        return None
    
    try:
        channel = await client.get_entity(channel_identifier)
        
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        
        total = len(message_ids)
        
        with progress_container:
            st.markdown("### 📦 Creating ZIP Archive")
            overall_progress = st.progress(0)
            overall_status = st.empty()
            
            current_file_info = st.empty()
            file_progress = st.progress(0)
            download_stats = st.empty()
            
            temp_files = []
            
            # Download all files to temp directory
            for idx, msg_id in enumerate(message_ids):
                message = await client.get_messages(channel, ids=msg_id)
                
                if message and message.media:
                    file_info = get_file_info(message)
                    
                    current_file_info.markdown(f"**📄 Downloading {idx + 1}/{total}:** `{file_info['name']}`")
                    
                    start_time = time.time()
                    last_update_time = start_time
                    
                    def progress_callback(current, total_size):
                        nonlocal last_update_time
                        current_time = time.time()
                        
                        if current_time - last_update_time >= 0.5 or current == total_size:
                            last_update_time = current_time
                            file_percent = (current / total_size * 100) if total_size > 0 else 0
                            file_progress.progress(current / total_size if total_size > 0 else 0)
                            
                            elapsed = current_time - start_time
                            if elapsed > 0:
                                speed = current / elapsed
                                download_stats.markdown(f"""
                                **Progress:** {format_size(current)} / {format_size(total_size)} ({file_percent:.1f}%)  
                                **Speed:** {format_speed(speed)}
                                """)
                    
                    # Download to temp directory
                    file_number = str(idx + 1).zfill(3)
                    custom_name = f"{file_number}_{file_info['name']}"
                    file_path = await message.download_media(
                        file=f"{temp_dir}/{custom_name}",
                        progress_callback=progress_callback
                    )
                    
                    if file_path:
                        temp_files.append((file_path, custom_name))
                    
                    overall_progress.progress((idx + 1) / total)
                    overall_status.markdown(f"**Downloaded:** {idx + 1} / {total} files")
            
            # Create ZIP file
            current_file_info.markdown("**📦 Creating ZIP archive...**")
            file_progress.progress(0)
            
            zip_path = f"downloads/{zip_name}"
            os.makedirs("downloads", exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for idx, (file_path, custom_name) in enumerate(temp_files):
                    zipf.write(file_path, custom_name)
                    file_progress.progress((idx + 1) / len(temp_files))
                    download_stats.markdown(f"**Adding to ZIP:** {idx + 1} / {len(temp_files)} files")
            
            # Clean up temp files
            for file_path, _ in temp_files:
                try:
                    os.remove(file_path)
                except:
                    pass
            
            try:
                os.rmdir(temp_dir)
            except:
                pass
            
            # Clear progress UI
            current_file_info.empty()
            file_progress.empty()
            download_stats.empty()
            overall_progress.empty()
            overall_status.empty()
            
            st.success(f"✅ ZIP archive created: `{zip_path}`")
            
            # Get file size
            zip_size = os.path.getsize(zip_path)
            st.info(f"📦 Archive size: {format_size(zip_size)}")
            
            # Don't disconnect - using shared client
            return zip_path
            
    except Exception as e:
        st.error(f"Export error: {e}")
        return None


# Streamlit UI
st.set_page_config(page_title="Telegram Media Downloader", page_icon="📥", layout="wide")

st.title("📥 Telegram Media Downloader")
st.markdown("Browse and download media from Telegram channels")

# Sidebar for input
with st.sidebar:
    st.header("Settings")
    channel_url = st.text_input(
        "Channel URL/ID",
        placeholder="https://t.me/c/2381311281/21",
        help="Enter Telegram channel URL or ID"
    )
    
    fetch_limit = st.slider("Number of messages to fetch", 100, 10000, 5000, 100)
    
    st.markdown("---")
    st.subheader("⚡ Download Settings")
    concurrent_downloads = st.slider(
        "Concurrent downloads", 
        1, 10, 3, 1,
        help="Download multiple files simultaneously for faster speed. Higher = faster but uses more bandwidth."
    )
    st.caption("💡 Tip: 3-5 concurrent downloads work best for most connections")
    
    # Video conversion option
    st.markdown("---")
    st.subheader("🎬 Video Settings")
    convert_videos = st.checkbox(
        "Auto-convert videos to MP4",
        value=True,
        help="Automatically convert downloaded videos to MP4 format with AAC audio (compatible with all players). Telegram videos use Opus codec which some players don't support."
    )
    if 'convert_videos' not in st.session_state:
        st.session_state.convert_videos = convert_videos
    else:
        st.session_state.convert_videos = convert_videos
    
    if not Path(FFMPEG_PATH).exists():
        st.warning("⚠️ FFmpeg not found. Video conversion disabled.")
        st.caption("Run setup_ffmpeg.py to enable conversion")
    
    st.markdown("---")
    
    fetch_button = st.button("🔍 Fetch Media", type="primary")

# Initialize session state
if 'media_list' not in st.session_state:
    st.session_state.media_list = []
if 'channel_info' not in st.session_state:
    st.session_state.channel_info = None
if 'topics_structure' not in st.session_state:
    st.session_state.topics_structure = {}
if 'selected_topic' not in st.session_state:
    st.session_state.selected_topic = "All"
if 'topic_names' not in st.session_state:
    st.session_state.topic_names = {}

# Fetch media
if fetch_button and channel_url:
    with st.spinner("Fetching media from channel..."):
        channel_id, url_topic_id = parse_channel_url(channel_url)
        
        if url_topic_id:
            st.info(f"📌 Fetching from specific topic/thread ID: {url_topic_id}")
        
        channel, messages, topics_structure, topic_names, fetched_topic_id = asyncio.run(
            fetch_media_list(channel_id, fetch_limit, url_topic_id)
        )
        
        if channel:
            st.session_state.channel_info = {
                "title": channel.title,
                "id": channel.id,
            }
            st.session_state.media_list = [get_file_info(msg) for msg in messages]
            st.session_state.messages_map = {msg.id: msg for msg in messages}
            st.session_state.topics_structure = topics_structure
            st.session_state.topic_names = topic_names
            st.session_state.url_topic_id = url_topic_id
            
            # Create topics info for UI
            st.session_state.topics_list = list(topics_structure.keys())
            
            if url_topic_id:
                st.success(f"Found {len(st.session_state.media_list)} media files from topic ID {url_topic_id}!")
            else:
                st.success(f"Found {len(st.session_state.media_list)} media files in {len(topics_structure)} folders!")

# Display media list
if st.session_state.media_list:
    st.header(f"📁 {st.session_state.channel_info['title']}")
    
    if 'url_topic_id' in st.session_state and st.session_state.url_topic_id:
        st.caption(f"Channel ID: {st.session_state.channel_info['id']} | 📌 Topic/Thread ID: {st.session_state.url_topic_id}")
    else:
        st.caption(f"Channel ID: {st.session_state.channel_info['id']}")
    
    # Display folder/topic structure
    if len(st.session_state.topics_structure) > 1:
        st.subheader("📂 Channel Structure")
        
        # Show topic statistics
        col_topics = st.columns(min(4, len(st.session_state.topics_structure)))
        for idx, (topic_name, topic_msgs) in enumerate(st.session_state.topics_structure.items()):
            with col_topics[idx % 4]:
                media_count = len([get_file_info(msg) for msg in topic_msgs])
                st.metric(topic_name, f"{media_count} files")
        
        st.markdown("---")
        
        # Topic selector
        selected_topic = st.selectbox(
            "Select Folder/Topic to view",
            ["All"] + st.session_state.topics_list,
            key="topic_selector"
        )
        st.session_state.selected_topic = selected_topic
    
    # Filter by selected topic
    if st.session_state.selected_topic != "All" and st.session_state.selected_topic in st.session_state.topics_structure:
        filtered_by_topic = [get_file_info(msg) for msg in st.session_state.topics_structure[st.session_state.selected_topic]]
        st.info(f"📂 Viewing: **{st.session_state.selected_topic}** ({len(filtered_by_topic)} files)")
    else:
        filtered_by_topic = st.session_state.media_list
        if len(st.session_state.topics_structure) > 1:
            st.info(f"📂 Viewing: **All Topics** ({len(filtered_by_topic)} files)")
    
    # Filter options
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_type = st.selectbox(
            "Filter by type",
            ["All", "Photo", "Video", "Document", "PDF", "ZIP", "Audio"]
        )
    
    # Filter media by type
    filtered_media = filtered_by_topic
    if filter_type != "All":
        filtered_media = [m for m in filtered_by_topic if m["type"] == filter_type]
    
    st.write(f"Showing {len(filtered_media)} files")
    
    # Batch download option with organized folders
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.session_state.selected_topic != "All":
            download_all = st.button(f"📥 Download All from '{st.session_state.selected_topic}'", type="primary", use_container_width=True)
        else:
            download_all = st.button("📥 Download All (Organized by Folders)", type="primary", use_container_width=True)
    
    with col2:
        if st.button("📦 Export All as ZIP", type="secondary", use_container_width=True):
            progress_container = st.container()
            channel_id, _ = parse_channel_url(channel_url)
            
            # Create ZIP filename
            channel_name = st.session_state.channel_info['title'].replace(' ', '_').replace('/', '_')
            filter_suffix = f"_{filter_type}" if filter_type != "All" else ""
            topic_suffix = f"_{st.session_state.selected_topic.replace(' ', '_')}" if st.session_state.selected_topic != "All" else "_All"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"{channel_name}{topic_suffix}{filter_suffix}_{timestamp}.zip"
            
            message_ids = [m["id"] for m in filtered_media]
            topic_for_export = st.session_state.selected_topic if st.session_state.selected_topic != "All" else None
            
            zip_path = asyncio.run(export_as_zip(channel_id, message_ids, zip_filename, progress_container, topic_for_export))
            
            if zip_path and os.path.exists(zip_path):
                with open(zip_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Download ZIP File",
                        data=file,
                        file_name=zip_filename,
                        mime="application/zip",
                        type="primary"
                    )
    
    with col3:
        st.write(f"Total size: {format_size(sum(m['size'] for m in filtered_media))}")
    
    if download_all:
        progress_container = st.container()
        
        channel_id, _ = parse_channel_url(channel_url)
        
        if st.session_state.selected_topic != "All":
            # Download from single topic
            message_ids = [m["id"] for m in filtered_media]
            asyncio.run(download_files(channel_id, message_ids, progress_container, st.session_state.selected_topic, concurrent_downloads))
        else:
            # Download all topics with organized folders
            with progress_container:
                st.markdown("### 📥 Batch Download Progress")
                overall_progress = st.progress(0)
                overall_status = st.empty()
                
                total_files = len(filtered_media)
                current = 0
                
                for topic_name, topic_msgs in st.session_state.topics_structure.items():
                    topic_media = [get_file_info(msg) for msg in topic_msgs]
                    if filter_type != "All":
                        topic_media = [m for m in topic_media if m["type"] == filter_type]
                    
                    if topic_media:
                        overall_status.markdown(f"📂 **Downloading from:** {topic_name}")
                        message_ids = [m["id"] for m in topic_media]
                        
                        # Download this topic
                        topic_container = st.container()
                        asyncio.run(download_files(channel_id, message_ids, topic_container, topic_name, concurrent_downloads))
                        
                        current += len(topic_media)
                        overall_progress.progress(current / total_files)
                
                overall_status.markdown(f"✅ **All downloads complete!** {total_files} files downloaded.")
                st.balloons()
    
    # Display media table with selection
    st.markdown("---")
    st.subheader("Media Files")
    
    # Pagination controls
    items_per_page = st.selectbox("Items per page", [50, 100, 200, 500, "All"], index=1)
    
    if items_per_page == "All":
        items_per_page = len(filtered_media)
    else:
        items_per_page = int(items_per_page)
    
    total_pages = max(1, (len(filtered_media) + items_per_page - 1) // items_per_page)
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("⬅️ Previous") and st.session_state.current_page > 1:
            st.session_state.current_page -= 1
            st.rerun()
    with col_nav2:
        st.write(f"Page {st.session_state.current_page} of {total_pages}")
    with col_nav3:
        if st.button("Next ➡️") and st.session_state.current_page < total_pages:
            st.session_state.current_page += 1
            st.rerun()
    
    # Calculate page slice
    start_idx = (st.session_state.current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(filtered_media))
    page_media = filtered_media[start_idx:end_idx]
    
    # Create selection column
    selected_items = []
    
    # Table header
    col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 1, 2, 1.5, 1])
    with col1:
        st.write("✓")
    with col2:
        st.write("**File Name**")
    with col3:
        st.write("**Type**")
    with col4:
        st.write("**Size**")
    with col5:
        st.write("**Date**")
    with col6:
        st.write("**Action**")
    
    st.markdown("---")
    
    # Display in table format
    for idx, media in enumerate(page_media):
        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 1, 2, 1.5, 1])
        
        with col1:
            selected = st.checkbox("Select", key=f"select_{media['id']}", label_visibility="collapsed")
            if selected:
                selected_items.append(media["id"])
        
        with col2:
            st.write(media["name"])
        
        with col3:
            st.write(media["type"])
        
        with col4:
            st.write(format_size(media["size"]))
        
        with col5:
            st.write(media["date"])
        
        with col6:
            if st.button("⬇️", key=f"download_{media['id']}"):
                progress_container = st.container()
                channel_id, _ = parse_channel_url(channel_url)
                # Find which topic this media belongs to
                topic_for_media = st.session_state.selected_topic if st.session_state.selected_topic != "All" else None
                asyncio.run(download_files(channel_id, [media["id"]], progress_container, topic_for_media, 1))
    
    # Download selected button
    if selected_items:
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"📥 Download Selected ({len(selected_items)} files)", type="primary", use_container_width=True):
                progress_container = st.container()
                channel_id, _ = parse_channel_url(channel_url)
                topic_for_selected = st.session_state.selected_topic if st.session_state.selected_topic != "All" else None
                asyncio.run(download_files(channel_id, selected_items, progress_container, topic_for_selected, concurrent_downloads))
        
        with col2:
            if st.button(f"📦 Export as ZIP ({len(selected_items)} files)", type="secondary", use_container_width=True):
                progress_container = st.container()
                channel_id, _ = parse_channel_url(channel_url)
                
                # Create ZIP filename
                channel_name = st.session_state.channel_info['title'].replace(' ', '_').replace('/', '_')
                topic_suffix = f"_{st.session_state.selected_topic.replace(' ', '_')}" if st.session_state.selected_topic != "All" else ""
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_filename = f"{channel_name}{topic_suffix}_{timestamp}.zip"
                
                topic_for_selected = st.session_state.selected_topic if st.session_state.selected_topic != "All" else None
                zip_path = asyncio.run(export_as_zip(channel_id, selected_items, zip_filename, progress_container, topic_for_selected))
                
                if zip_path and os.path.exists(zip_path):
                    # Provide download button
                    with open(zip_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Download ZIP File",
                            data=file,
                            file_name=zip_filename,
                            mime="application/zip",
                            type="primary"
                        )

else:
    st.info("👈 Enter a channel URL in the sidebar and click 'Fetch Media' to get started!")
    
    st.markdown("""
    ### Supported URL formats:
    - `https://t.me/c/2381311281/21` (private channel)
    - `https://web.telegram.org/a/#-1002381311281`
    - `https://t.me/channelname`
    - `-1002381311281` (direct ID)
    - `@channelname` or `channelname`
    
    ### Features:
    - 📋 Browse all media in the channel
    - 🎯 Filter by media type (Photo, Video, PDF, etc.)
    - ✅ Select specific files to download
    - 📦 Batch download all or filtered files
    - 📊 View file details (name, size, date)
    """)
