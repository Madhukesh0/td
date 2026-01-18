@echo off
echo ========================================
echo  Telegram Media Downloader
echo  GitHub + Streamlit Cloud Deployment
echo ========================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed!
    echo Please install Git from: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo Step 1: Initialize Git Repository
echo ----------------------------------------
git init
if errorlevel 1 (
    echo Git repository already initialized
)
echo.

echo Step 2: Add all files to Git
echo ----------------------------------------
git add .
echo.

echo Step 3: Commit changes
echo ----------------------------------------
set /p commit_msg="Enter commit message (or press Enter for default): "
if "%commit_msg%"=="" set commit_msg=Initial deployment commit

git commit -m "%commit_msg%"
echo.

echo Step 4: Set main branch
echo ----------------------------------------
git branch -M main
echo.

echo ========================================
echo  IMPORTANT: Create GitHub Repository
echo ========================================
echo.
echo 1. Go to: https://github.com/new
echo 2. Repository name: telegram-media-downloader
echo 3. Keep it PUBLIC
echo 4. DON'T initialize with README
echo 5. Click "Create repository"
echo.
pause

echo.
echo Step 5: Add GitHub remote
echo ----------------------------------------
set /p github_user="Enter your GitHub username: "
set github_url=https://github.com/%github_user%/telegram-media-downloader.git

git remote add origin %github_url% 2>nul
if errorlevel 1 (
    echo Remote origin already exists, updating URL...
    git remote set-url origin %github_url%
)
echo.

echo Step 6: Push to GitHub
echo ----------------------------------------
echo Pushing to: %github_url%
git push -u origin main
if errorlevel 1 (
    echo.
    echo ERROR: Push failed!
    echo.
    echo Possible reasons:
    echo 1. GitHub repository doesn't exist
    echo 2. Authentication failed
    echo 3. Repository URL is incorrect
    echo.
    echo Try these solutions:
    echo - Make sure you created the repository on GitHub
    echo - Check your GitHub credentials
    echo - Use 'git push -u origin main --force' if needed
    echo.
    pause
    exit /b 1
)
echo.

echo ========================================
echo  SUCCESS! Code pushed to GitHub
echo ========================================
echo.
echo Repository URL: %github_url%
echo.

echo ========================================
echo  NEXT: Deploy to Streamlit Cloud
echo ========================================
echo.
echo Follow these steps:
echo.
echo 1. Go to: https://share.streamlit.io
echo.
echo 2. Click "New app"
echo.
echo 3. Connect your GitHub account (if not connected)
echo.
echo 4. Fill in the form:
echo    - Repository: %github_user%/telegram-media-downloader
echo    - Branch: main
echo    - Main file path: src/app_cloud.py
echo    - Python version: 3.11
echo.
echo 5. Click "Deploy"!
echo.
echo 6. Your app will be live at:
echo    https://YOUR-APP-NAME.streamlit.app
echo.
echo ========================================
echo  OPTIONAL: View Your Repository
echo ========================================
echo.
set /p open_browser="Open GitHub repository in browser? (Y/N): "
if /i "%open_browser%"=="Y" (
    start %github_url%
)
echo.

echo ========================================
echo  Deployment script completed!
echo ========================================
echo.
echo What to do next:
echo 1. Visit https://share.streamlit.io to deploy
echo 2. Share your app URL with users
echo 3. Users will need their own API credentials from:
echo    https://my.telegram.org/apps
echo.
pause
