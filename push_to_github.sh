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
  git -C /home/runner/workspace commit -m "fix: correct ffmpeg-kit artifact name + revert yt-dlp version pin

build.gradle:
- ffmpeg-kit-audio-gpl does not exist on Maven Central — use
  com.arthenica:ffmpeg-kit-full-gpl:6.0.LTS (confirmed available)
  Covers: H.263 (3GP), libmp3lame (MP3), libx264 (MP4 H.264)
- Revert yt-dlp version pin: Chaquopy mirror only has 2024.10.22,
  pinning >=2026.3.17 would cause a Chaquopy resolution failure;
  leave unpinned so Chaquopy uses latest it can resolve"
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
