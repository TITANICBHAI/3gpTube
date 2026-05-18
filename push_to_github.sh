#!/bin/bash
set -e

REPO="TITANICBHAI/3gpTube"

echo "=== 3gpTube - Push to GitHub ==="

unset GIT_ASKPASS
unset SSH_ASKPASS
export GIT_TERMINAL_PROMPT=0

TOKEN=$(echo -n "${GITHUB_PERSONAL_ACCESS_TOKEN}" | tr -d '[:space:]')

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
  git -C /home/runner/workspace commit -m "feat: add Direct Download (no FFmpeg) format to web + Android

Web app (app.py + templates/index.html + templates/search.html):
- Add 'direct' format: yt-dlp best[ext=mp4]/best[ext=webm]/best
- Skip FFmpeg entirely — detect actual extension, rename temp file
- Allow 'direct' in convert route; quality auto-set to 'auto'
- Add quality_preset stub so status logging doesn't crash
- Add Direct Download radio button + info panel to index.html
- Add Direct radio + info panel to search.html per result

Android (flask_server.py + both templates):
- Add is_direct flag; fmt_str uses pre-muxed stream selector
- Post-download: detect extension, rename, mark completed with no FFmpeg
- Direct skips retry strategies same as native
- Add Direct Download radio to android index.html + search.html
- Note 3GP/MP4 now show 'Requires FFmpeg on device' warning

Motivation: Android APK ships no FFmpeg binary; 3GP silently
falls back to MP4 and MP3 postprocessor also needs FFmpeg.
Direct Download is the recommended Android-safe format."
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
