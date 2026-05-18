#!/bin/bash
set -e

REPO="TITANICBHAI/3gpTube"

echo "=== 3gpTube - Push to GitHub ==="

git config --global user.email "bot@3gptube.dev"
git config --global user.name "3gpTube Bot"

unset GIT_ASKPASS
unset SSH_ASKPASS
export GIT_TERMINAL_PROMPT=0

git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"

echo "[1] Staging all changes..."
git add -A

echo "[2] Committing..."
if git diff --cached --quiet; then
  echo "[INFO] Nothing new to commit"
else
  git commit -m "feat: WebView + local Flask server via Chaquopy

- Replace native Android UI fragments with full-screen WebView
- Flask server starts locally on device via Chaquopy Python bridge
- WebView loads http://127.0.0.1:5000 (fully offline except yt-dlp)
- Templates bundled inside APK (base, index, mp3, 3gp, search, history, status)
- Added flask, jinja2, werkzeug to Chaquopy pip installs
- MainActivity: starts Flask in coroutine, polls /ping, then loads WebView
- Supports YouTube share intent (pre-fills URL in web UI)
- Back button navigates WebView history
- Cleartext traffic enabled for localhost
- Removed unused native fragments, ViewModels, adapters"
fi

echo "[3] Pushing to GitHub..."
GIT_ASKPASS=/bin/echo git push origin HEAD:main || GIT_ASKPASS=/bin/echo git push origin HEAD:master

echo ""
echo "[OK] Pushed to https://github.com/${REPO}"
echo "[OK] GitHub Actions will now build the APK"
echo "[OK] Watch: https://github.com/${REPO}/actions"
