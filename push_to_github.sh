#!/bin/bash
set -e

REPO="TITANICBHAI/3gpTube"

echo "=== 3gpTube - Push to GitHub ==="

git config --global user.email "bot@3gptube.dev"
git config --global user.name "3gpTube Bot"
git config --global http.extraHeader "Authorization: Bearer ${GITHUB_TOKEN}"

git remote set-url origin "https://github.com/${REPO}.git"

echo "[1] Staging all changes..."
git add -A

echo "[2] Committing..."
git diff --cached --quiet && echo "[INFO] Nothing new to commit" || \
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

echo "[3] Pushing to GitHub..."
git push origin HEAD:main 2>&1 || git push origin HEAD:master 2>&1

echo ""
echo "[OK] Pushed to https://github.com/${REPO}"
echo "[OK] GitHub Actions will now build the APK automatically"
echo "[OK] Watch build at: https://github.com/${REPO}/actions"
