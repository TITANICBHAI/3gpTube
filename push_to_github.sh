#!/bin/bash
set -e

REPO="TITANICBHAI/3gpTube"

echo "=== 3gpTube - Push to GitHub ==="

git config --global user.email "bot@3gptube.dev"
git config --global user.name "3gpTube Bot"

unset GIT_ASKPASS
unset SSH_ASKPASS
export GIT_TERMINAL_PROMPT=0

TOKEN=$(echo -n "${GITHUB_TOKEN}" | tr -d '[:space:]')

# Build Basic auth header: base64("x-access-token:TOKEN")
AUTH=$(echo -n "x-access-token:${TOKEN}" | base64 -w 0)
git config --global http.https://github.com/.extraheader "Authorization: Basic ${AUTH}"

git remote set-url origin "https://github.com/${REPO}.git"

echo "[1] Staging all changes..."
git add -A

echo "[2] Committing..."
if git diff --cached --quiet; then
  echo "[INFO] Nothing new to commit"
else
  git commit -m "feat: WebView + local Flask server via Chaquopy

- Replace native Android UI with full-screen WebView
- Flask server starts locally on device via Chaquopy Python bridge
- WebView loads http://127.0.0.1:5000 (fully offline except yt-dlp)
- Templates bundled inside APK
- Added flask, jinja2, werkzeug to Chaquopy pip installs
- Removed unused native fragments, ViewModels, adapters"
fi

echo "[3] Pushing to GitHub..."
git push origin HEAD:main 2>&1 && echo "[OK] Pushed to main" || \
  git push origin HEAD:master 2>&1 && echo "[OK] Pushed to master"

echo ""
echo "[OK] Done! Watch build at: https://github.com/${REPO}/actions"
