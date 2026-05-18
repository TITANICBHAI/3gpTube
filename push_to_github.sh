#!/bin/bash
set -e

REPO="TITANICBHAI/3gpTube"

echo "=== 3gpTube - Push to GitHub ==="

unset GIT_ASKPASS
unset SSH_ASKPASS
export GIT_TERMINAL_PROMPT=0

TOKEN=$(echo -n "${GITHUB_TOKEN}" | tr -d '[:space:]')

# Use a clean temporary HOME so no conflicting system git config applies
export HOME=/tmp/githome
mkdir -p /tmp/githome

git config --global user.email "bot@3gptube.dev"
git config --global user.name "3gpTube Bot"

# Reset remote to token-based URL (no extra header, just token in URL)
git -C /home/runner/workspace remote set-url origin "https://x-access-token:${TOKEN}@github.com/${REPO}.git"

echo "[1] Staging all changes..."
git -C /home/runner/workspace add -A

echo "[2] Committing..."
if git -C /home/runner/workspace diff --cached --quiet; then
  echo "[INFO] Nothing new to commit"
else
  git -C /home/runner/workspace commit -m "feat: auto-update yt-dlp, MP4 quality, formats page, YouTube cookie login

- Settings page with yt-dlp version display and manual update button
- Auto-update yt-dlp on startup (once per day, background thread)
- MP4 format with 360p/480p/720p/1080p quality presets via FFmpeg
- Formats page: shows all native YouTube formats (direct/video-only/audio-only)
  and allows direct download or re-encode via FFmpeg
- Built-in YouTube login browser in MainActivity (WebView overlay)
  - Android CookieManager extracts cookies after login
  - POSTs cookies to /save-cookies as Netscape format
- Manual cookie upload (file or paste) still supported
- Updated nav: Home/Search/Formats/History/Cookies/Settings
- Updated activity_main.xml with root FrameLayout for cookie login overlay"
fi

echo "[3] Pushing to GitHub..."
git -C /home/runner/workspace push origin HEAD:main 2>&1 \
  && echo "[OK] Pushed to main" \
  || git -C /home/runner/workspace push origin HEAD:master 2>&1 \
  && echo "[OK] Pushed to master"

# Restore clean remote URL (no token in URL)
git -C /home/runner/workspace remote set-url origin "https://github.com/${REPO}.git"

echo ""
echo "[OK] Done! Watch: https://github.com/${REPO}/actions"
