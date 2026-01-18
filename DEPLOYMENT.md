# 🚀 Cloud Deployment Guide - Free Hosting

## Deploy Telegram Media Downloader for FREE

Your app can now be used by anyone worldwide for **FREE**! This guide covers multiple free hosting platforms.

---

## 📋 Prerequisites

Before deployment:

1. ✅ A GitHub account (free)
2. ✅ Your repository pushed to GitHub
3. ✅ Users will need their own Telegram API credentials from https://my.telegram.org/apps

---

## 🎯 Option 1: Streamlit Cloud (Recommended - Easiest)

### Features:

- ✅ **100% Free** forever
- ✅ Unlimited public apps
- ✅ Auto-deploys from GitHub
- ✅ Built-in SSL/HTTPS
- ✅ No credit card required

### Step-by-Step:

1. **Prepare Repository**

   ```bash
   # Make sure these files are in your repo:
   # - src/app_cloud.py (cloud version)
   # - requirements.txt
   # - packages.txt (for FFmpeg)
   # - .streamlit/config.toml
   ```

2. **Push to GitHub**

   ```bash
   cd telegram-media-downloader
   git init
   git add .
   git commit -m "Ready for cloud deployment"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/telegram-media-downloader.git
   git push -u origin main
   ```

3. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect your GitHub account
   - Select your repository
   - Set:
     - **Main file path**: `src/app_cloud.py`
     - **Python version**: 3.11
   - Click "Deploy"!

4. **Your App is Live! 🎉**
   - URL: `https://your-app-name.streamlit.app`
   - Share this with anyone!

---

## 🎯 Option 2: Railway.app

### Features:

- ✅ **$5 free credit/month**
- ✅ Auto-deploys from GitHub
- ✅ Supports larger files
- ✅ Custom domains

### Step-by-Step:

1. **Create `railway.json`**

   ```json
   {
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "streamlit run src/app_cloud.py --server.port $PORT --server.address 0.0.0.0",
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 10
     }
   }
   ```

2. **Create `Procfile`**

   ```
   web: streamlit run src/app_cloud.py --server.port $PORT --server.address 0.0.0.0
   ```

3. **Deploy**
   - Go to https://railway.app
   - Click "Start a New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway auto-detects and deploys!

---

## 🎯 Option 3: Render.com

### Features:

- ✅ **Free tier** (750 hours/month)
- ✅ Auto-deploy from GitHub
- ✅ Good for moderate traffic

### Step-by-Step:

1. **Create `render.yaml`**

   ```yaml
   services:
     - type: web
       name: telegram-downloader
       env: python
       buildCommand: "pip install -r requirements.txt && apt-get update && apt-get install -y ffmpeg"
       startCommand: "streamlit run src/app_cloud.py --server.port $PORT --server.address 0.0.0.0"
       plan: free
   ```

2. **Deploy**
   - Go to https://render.com
   - Click "New" → "Web Service"
   - Connect GitHub repository
   - Render auto-deploys!

---

## 📝 Configuration Files Created

### 1. `src/app_cloud.py`

**Cloud-optimized version** with:

- ✅ Multi-user support
- ✅ User authentication (each user provides their own API credentials)
- ✅ Session string support (users can save and reuse sessions)
- ✅ Temporary file storage (auto-cleanup)
- ✅ ZIP download (no persistent storage needed)
- ✅ FFmpeg auto-detection across platforms

### 2. `requirements.txt`

```
Telethon==1.38.1
streamlit>=1.30.0
nest-asyncio>=1.5.8
python-dotenv==1.0.1
cryptg==0.5.0.post0
```

### 3. `packages.txt`

```
ffmpeg
```

(Installs FFmpeg on cloud platforms)

### 4. `.streamlit/config.toml`

Server configuration for cloud deployment

---

## 🔐 Security Features

### Built-in Security:

1. **No Shared Sessions**: Each user uses their own credentials
2. **No Server Storage**: Sessions stored in browser only
3. **Temporary Downloads**: Files deleted after ZIP creation
4. **API Credentials**: Never logged or stored on server
5. **Session Strings**: Optional - users can save for convenience

### User Flow:

1. User visits your app
2. Enters their own API ID/Hash from my.telegram.org
3. Logs in with phone + verification code
4. Gets a session string to save (optional)
5. Downloads media
6. Logs out (session cleared from server)

---

## 💡 Usage Instructions for Your Users

### First-Time Users:

1. **Get API Credentials** (one-time setup)
   - Visit https://my.telegram.org/apps
   - Log in with your Telegram account
   - Click "Create Application"
   - Copy **API ID** and **API Hash**

2. **Use the App**
   - Open the deployed app URL
   - Enter API ID and API Hash
   - Enter phone number (with country code, e.g., +1234567890)
   - Click "Send Code"
   - Enter verification code from Telegram
   - **Save the session string** shown (optional but recommended!)

3. **Download Media**
   - Enter channel URL
   - Click "Fetch Media"
   - Select files to download
   - Click "Download Selected"
   - Click "Download ZIP" when ready

### Returning Users:

1. Enter saved API credentials
2. Paste saved session string
3. Click "Connect with Session"
4. Start downloading immediately!

---

## ⚙️ Customization

### Modify Download Limits:

Edit `src/app_cloud.py`:

```python
# Line ~700
fetch_limit = st.slider("Messages to fetch", 100, 5000, 1000, 100)
# Change to:
fetch_limit = st.slider("Messages to fetch", 100, 10000, 2000, 100)
```

### Change Concurrent Downloads:

```python
# Line ~710
concurrent_downloads = st.slider("Concurrent downloads", 1, 5, 2, 1)
# Change to:
concurrent_downloads = st.slider("Concurrent downloads", 1, 10, 3, 1)
```

### Disable Video Conversion:

```python
# Line ~715
convert_videos = st.checkbox("Auto-convert to MP4", value=bool(FFMPEG_PATH))
# Change to:
convert_videos = st.checkbox("Auto-convert to MP4", value=False)
```

---

## 📊 Platform Comparison

| Platform            | Free Tier          | Setup              | FFmpeg | Custom Domain |
| ------------------- | ------------------ | ------------------ | ------ | ------------- |
| **Streamlit Cloud** | ✅ Unlimited       | ⭐⭐⭐⭐⭐ Easiest | ✅ Yes | ❌ No         |
| **Railway**         | ✅ $5/month credit | ⭐⭐⭐⭐ Easy      | ✅ Yes | ✅ Yes        |
| **Render**          | ✅ 750 hrs/month   | ⭐⭐⭐ Medium      | ✅ Yes | ✅ Yes        |

---

## 🐛 Troubleshooting

### App Won't Start:

1. Check logs in deployment dashboard
2. Verify all files are pushed to GitHub
3. Ensure `src/app_cloud.py` exists
4. Check Python version is 3.9+

### FFmpeg Not Working:

1. Verify `packages.txt` exists with `ffmpeg`
2. Check platform supports apt packages
3. Video conversion will be disabled (still works, just no conversion)

### Users Can't Authenticate:

1. Tell users to double-check API credentials
2. Ensure phone number has country code (+)
3. Try clearing browser cache
4. Generate new session by logging in fresh

### App Too Slow:

1. Reduce concurrent downloads
2. Limit fetch messages to 1000-2000
3. Consider Railway/Render for better performance
4. Users can deploy their own instance!

---

## 🎉 Next Steps

1. **Deploy** using one of the options above
2. **Test** with your own Telegram account
3. **Share** the URL with users
4. **Document** in README how users get API credentials
5. **Monitor** usage in platform dashboard

---

## 🔗 Useful Links

- **Streamlit Cloud**: https://share.streamlit.io
- **Railway**: https://railway.app
- **Render**: https://render.com
- **Get Telegram API**: https://my.telegram.org/apps
- **Streamlit Docs**: https://docs.streamlit.io/streamlit-community-cloud

---

## 💰 Cost Breakdown

### Streamlit Cloud:

- **Cost**: $0/month
- **Limits**: Unlimited public apps
- **Best for**: Public tools, demos, portfolios

### Railway:

- **Cost**: $5 free credit/month = ~500 hours
- **Upgrade**: $5/month for more resources
- **Best for**: Personal use, team tools

### Render:

- **Cost**: Free tier = 750 hours/month
- **Limitations**: Spins down after inactivity
- **Best for**: Low-traffic apps

---

## ✨ Your App is Now Deployed!

Users worldwide can now:

- 📥 Download Telegram media
- 🎬 Convert videos to MP4
- ⚡ Use concurrent downloads
- 📦 Export as ZIP
- 🔐 Securely with their own credentials

**No cost to you, free for all users!** 🎉

---

## 🆘 Need Help?

If deployment fails:

1. Check platform logs
2. Verify all files are committed
3. Test locally first: `streamlit run src/app_cloud.py`
4. Open an issue on GitHub

**Happy Deploying! 🚀**
