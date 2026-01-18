# 🚀 Quick Deployment Guide

## Deploy in 5 Minutes!

### Prerequisites:

- ✅ Git installed (download from https://git-scm.com/download/win)
- ✅ GitHub account (free at https://github.com)

---

## 🎯 Automatic Deployment (Easiest)

### Windows:

1. **Double-click** `deploy.bat`
2. Follow the prompts:
   - Enter your GitHub username
   - Create repository on GitHub when prompted
   - Push code automatically
3. Go to https://share.streamlit.io and deploy!

---

## 📝 Manual Deployment (Step by Step)

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `telegram-media-downloader`
3. Make it **PUBLIC**
4. **DON'T** check "Initialize with README"
5. Click **Create repository**

### Step 2: Push Code to GitHub

Open PowerShell in this folder and run:

```powershell
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial deployment"

# Set main branch
git branch -M main

# Add GitHub remote (replace YOUR-USERNAME)
git remote add origin https://github.com/YOUR-USERNAME/telegram-media-downloader.git

# Push to GitHub
git push -u origin main
```

### Step 3: Deploy on Streamlit Cloud

1. Go to **https://share.streamlit.io**

2. Click **"New app"**

3. **Connect GitHub** (if not already connected)

4. Fill in the form:

   ```
   Repository: YOUR-USERNAME/telegram-media-downloader
   Branch: main
   Main file path: src/app_cloud.py
   Python version: 3.11
   ```

5. Click **"Deploy"**!

6. Wait 2-3 minutes for deployment

7. Your app will be live at:
   ```
   https://your-app-name.streamlit.app
   ```

---

## ✅ Verify Deployment

After deployment, test:

1. Open your app URL
2. Try authentication with test credentials
3. Fetch a public channel
4. Download a small file
5. Verify video conversion works

---

## 🎉 You're Live!

Share your app URL with anyone! They can:

- Download media from Telegram
- Convert videos to MP4
- Export as ZIP files

**No cost for you or your users!**

---

## 🔧 Update Your App

When you make changes:

```powershell
git add .
git commit -m "Update features"
git push
```

Streamlit Cloud auto-deploys updates in ~2 minutes!

---

## 📞 Need Help?

Check these if deployment fails:

### Git not found:

- Install: https://git-scm.com/download/win
- Restart PowerShell after installation

### Push failed:

```powershell
# Force push (use carefully!)
git push -u origin main --force
```

### Authentication issues:

- Use GitHub Personal Access Token
- Or use SSH keys
- Guide: https://docs.github.com/en/authentication

### Streamlit deployment errors:

- Check logs in Streamlit dashboard
- Verify `src/app_cloud.py` exists
- Ensure `requirements.txt` is correct

---

## 🌟 Pro Tips

1. **Custom Domain**: Upgrade Streamlit plan for custom URLs
2. **Private Repo**: Deploy from private repos (requires Streamlit team plan)
3. **Environment Variables**: Set secrets in Streamlit settings (if needed)
4. **Analytics**: Add Google Analytics to track usage
5. **Monitoring**: Check Streamlit logs for errors

---

## 📊 Post-Deployment Checklist

- [ ] App loads without errors
- [ ] Authentication works
- [ ] Can fetch channel media
- [ ] Downloads work
- [ ] Video conversion functions
- [ ] ZIP export successful
- [ ] Share app URL

---

**Ready to deploy? Run `deploy.bat` or follow manual steps!** 🚀
