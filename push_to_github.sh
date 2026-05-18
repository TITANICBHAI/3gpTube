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
  git -C /home/runner/workspace commit -m "feat: playlist support with preview, per-video selection, queue integration

- is_playlist_url() detects all YouTube playlist URL patterns
- get_playlist_info() fetches up to 50 entries flat (no download)
- /convert auto-detects playlist URLs and redirects to /playlist preview
- /playlist GET: shows playlist title, uploader, scrollable video list
  with checkboxes (select all / none), format + quality picker
- /playlist/add POST: queues only the selected videos, redirects to /queue
- /queue now shows [X videos added from playlist] confirmation banner
- [Playlist] added to nav for direct access
- queue.html and base.html updated accordingly"
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
