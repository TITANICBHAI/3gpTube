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
  git -C /home/runner/workspace commit -m "fix: bundle ffmpeg-kit-audio-gpl + upgrade yt-dlp in Android APK

android-app/app/build.gradle:
- Add com.arthenica:ffmpeg-kit-audio-gpl:6.0.LTS dependency
  Provides H.263 (3GP), libmp3lame (MP3), libx264 (MP4) on Android
  as a native .aar library — no binary to bundle manually
- Pin yt-dlp>=2026.3.17 (was getting 2024.10.22 from Chaquopy mirror)

android-app/app/src/main/python/flask_server.py:
- _find_ffmpeg(): try ffmpeg-kit via Chaquopy Java bridge first;
  returns '__ffmpeg_kit__' sentinel if available, else binary path
- Add _FFmpegResult class: subprocess-compatible return object
- Add _run_ffmpeg(cmd, timeout): unified runner — if cmd[0] is
  '__ffmpeg_kit__', calls FFmpegKit.execute() via Chaquopy Java bridge;
  otherwise falls through to subprocess.run() (desktop behaviour)
- Replace all 3 subprocess.run([ffmpeg,...]) calls with _run_ffmpeg()
  (MP3, 3GP, MP4 conversion paths all covered)"
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
