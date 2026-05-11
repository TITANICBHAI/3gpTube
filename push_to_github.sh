#!/bin/bash
set -e

echo "================================"
echo "  YouTube Converter — Push to GitHub"
echo "================================"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN environment variable not set."
    echo "Set it with: export GITHUB_TOKEN=your_token_here"
    echo "Or add it to Replit Secrets."
    exit 1
fi

if [ -z "$GITHUB_REPO" ]; then
    echo "ERROR: GITHUB_REPO not set. Example: youruser/youtube-converter-android"
    echo "Set it with: export GITHUB_REPO=youruser/reponame"
    exit 1
fi

BRANCH="${GITHUB_BRANCH:-main}"

REMOTE_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"

if ! git remote get-url origin &>/dev/null; then
    echo "Adding remote origin..."
    git remote add origin "$REMOTE_URL"
else
    echo "Updating remote origin..."
    git remote set-url origin "$REMOTE_URL"
fi

echo ""
echo "Staging all changes..."
git add -A

if git diff --cached --quiet; then
    echo "Nothing to commit. Forcing empty commit to trigger build..."
    git commit --allow-empty -m "ci: trigger APK build $(date '+%Y-%m-%d %H:%M:%S')"
else
    COMMIT_MSG="${1:-"feat: update Android app $(date '+%Y-%m-%d %H:%M:%S')"}"
    git commit -m "$COMMIT_MSG"
fi

echo ""
echo "Pushing to GitHub ($GITHUB_REPO / $BRANCH)..."
git push -u origin "$BRANCH" --force-with-lease 2>/dev/null || git push -u origin "$BRANCH" --force

echo ""
echo "================================"
echo "Push complete!"
echo "GitHub Actions is now building your APK."
echo ""
echo "Track the build:"
echo "  https://github.com/$GITHUB_REPO/actions"
echo ""
echo "Or run: ./watch_build.sh"
echo "================================"
