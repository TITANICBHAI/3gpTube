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
  git -C /home/runner/workspace commit -m "fix: remove broken ffmpeg-kit dep; M4A fallback + Direct as Android default

build.gradle:
- Remove com.arthenica:ffmpeg-kit-full-gpl — library is abandoned,
  all GitHub release assets removed, Maven Central entries are 404,
  GitHub Packages requires auth; no reliable distribution path exists.
  _run_ffmpeg() bridge kept as future-ready infrastructure.

flask_server.py:
- MP3 without FFmpeg: instead of broken FFmpegExtractAudio postprocessor,
  download native AAC/M4A audio stream directly (bestaudio[ext=m4a]);
  M4A plays natively on all Android devices without conversion.
- M4A fallback detects actual downloaded extension (m4a/aac/webm/opus).

android templates/index.html:
- Rename 'Direct Download (No FFmpeg)' -> 'Direct Download (Recommended)'
- Set Direct Download as DEFAULT selected format on page load
- Update info panel copy to be clearer about Android compatibility"
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
