#!/bin/bash
set -e

REPO_URL="https://github.com/TITANICBHAI/3gpTube.git"

echo "=== 3gpTube - Push to GitHub ==="

if ! git --no-optional-locks status &>/dev/null; then
    echo "[ERROR] Not a git repository"
    exit 1
fi

git remote set-url origin "$REPO_URL" 2>/dev/null || git remote add origin "$REPO_URL"

echo "[1] Staging all changes..."
git add -A

echo "[2] Committing..."
git commit -m "feat: WebView + local Flask server via Chaquopy

- Replace native Android UI fragments with full-screen WebView
- Flask server starts locally on device via Chaquopy Python bridge
- WebView loads http://127.0.0.1:5000 (fully offline except yt-dlp)
- Templates bundled inside APK (base.html, index, mp3, 3gp, search, history, status)
- Added flask, jinja2, werkzeug to Chaquopy pip installs
- Updated MainActivity: starts Flask in coroutine, polls /ping, then loads WebView
- Supports YouTube share intent (pre-fills URL in web UI)
- Back button navigates WebView history
- Cleartext traffic enabled for localhost only" 2>/dev/null || echo "[INFO] Nothing new to commit"

echo "[3] Pushing to GitHub..."
git push origin main --force-with-lease 2>/dev/null || git push origin master --force-with-lease 2>/dev/null || git push origin HEAD

echo ""
echo "[OK] Pushed to $REPO_URL"
echo "[OK] GitHub Actions will now build the APK automatically"
echo "[OK] Check: https://github.com/TITANICBHAI/3gpTube/actions"
