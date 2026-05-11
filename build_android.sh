#!/bin/bash
set -e

echo "================================================"
echo "   YouTube Converter — Build Android APK"
echo "================================================"
echo ""

# ── Check required env vars ──────────────────────────
if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN is not set."
    echo ""
    echo "  1. Go to https://github.com/settings/tokens"
    echo "  2. Generate a token with 'repo' scope"
    echo "  3. Add it to Replit Secrets as GITHUB_TOKEN"
    exit 1
fi

if [ -z "$GITHUB_REPO" ]; then
    echo "ERROR: GITHUB_REPO is not set."
    echo ""
    echo "  Set it to your GitHub repo (user/repo format):"
    echo "  export GITHUB_REPO=youruser/youtube-converter-android"
    echo "  Or add it to Replit Secrets."
    exit 1
fi

BRANCH="${GITHUB_BRANCH:-main}"
COMMIT_MSG="${1:-"build: update Android app $(date '+%Y-%m-%d %H:%M:%S')"}"
API="https://api.github.com/repos/$GITHUB_REPO"
AUTH_HEADER="Authorization: token $GITHUB_TOKEN"
ACCEPT_HEADER="Accept: application/vnd.github.v3+json"

_api() { curl -s -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" "$@"; }

# ── Step 1: Push to GitHub ───────────────────────────
echo "[1/3] Pushing code to GitHub ($GITHUB_REPO)..."
echo ""

REMOTE_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"
if ! git remote get-url origin &>/dev/null 2>&1; then
    git remote add origin "$REMOTE_URL"
else
    git remote set-url origin "$REMOTE_URL"
fi

git add -A

if git diff --cached --quiet; then
    echo "  Nothing new to commit — adding trigger commit..."
    git commit --allow-empty -m "ci: trigger APK build $(date '+%Y-%m-%d %H:%M:%S')"
else
    git commit -m "$COMMIT_MSG"
fi

git push -u origin "$BRANCH" --force-with-lease 2>/dev/null || git push -u origin "$BRANCH" --force

PUSH_TIME=$(date +%s)
echo ""
echo "  Pushed at $(date '+%H:%M:%S')"
echo "  https://github.com/$GITHUB_REPO/actions"
echo ""

# ── Step 2: Wait for workflow run to appear ──────────
echo "[2/3] Waiting for GitHub Actions to pick up the build..."
echo ""

POLL=10
RUN_ID=""
ELAPSED=0

while [ $ELAPSED -lt 120 ]; do
    sleep $POLL
    ELAPSED=$((ELAPSED + POLL))

    RUN_ID=$(_api "$API/actions/runs?per_page=5&event=push&branch=$BRANCH" | python3 -c "
import sys, json, datetime, time
data = json.load(sys.stdin)
push_time = $PUSH_TIME
for r in data.get('workflow_runs', []):
    try:
        t = datetime.datetime.strptime(r['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        ts = (t - datetime.datetime(1970,1,1)).total_seconds()
        if ts >= push_time - 60:
            print(r['id'])
            break
    except Exception:
        pass
" 2>/dev/null)

    if [ -n "$RUN_ID" ]; then
        echo "  Run found: #$RUN_ID"
        break
    fi

    MINS=$((ELAPSED / 60)); SECS=$((ELAPSED % 60))
    printf "  [%02d:%02d] Waiting for run to appear...\n" "$MINS" "$SECS"
done

if [ -z "$RUN_ID" ]; then
    # Fallback: grab the most recent run at all
    RUN_ID=$(_api "$API/actions/runs?per_page=1" | python3 -c "
import sys, json
runs = json.load(sys.stdin).get('workflow_runs', [])
print(runs[0]['id'] if runs else '')
" 2>/dev/null)
fi

if [ -z "$RUN_ID" ]; then
    echo ""
    echo "Could not find any workflow run. Check manually:"
    echo "  https://github.com/$GITHUB_REPO/actions"
    exit 1
fi

# ── Step 3: Watch the build live ─────────────────────
echo ""
echo "[3/3] Watching build #$RUN_ID..."
echo "  Live: https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
echo ""
printf "  %-9s  %-20s  %s\n" "TIME" "STATUS" "CURRENT STEP"
printf "  %-9s  %-20s  %s\n" "─────────" "────────────────────" "─────────────────────────────"

ELAPSED=0
MAX_WAIT=1800  # 30 min max

while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep $POLL
    ELAPSED=$((ELAPSED + POLL))

    RUN_DATA=$(_api "$API/actions/runs/$RUN_ID")
    STATUS=$(echo "$RUN_DATA"     | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))"     2>/dev/null)
    CONCLUSION=$(echo "$RUN_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('conclusion',''))" 2>/dev/null)

    STEP=$(_api "$API/actions/runs/$RUN_ID/jobs" | python3 -c "
import sys, json
data = json.load(sys.stdin)
jobs = data.get('jobs', [])
if not jobs:
    print('Queued')
    exit()
steps = jobs[0].get('steps', [])
active = [s['name'] for s in steps if s.get('status') == 'in_progress']
if active:
    print(active[0])
    exit()
done = [s['name'] for s in steps if s.get('status') == 'completed']
print(done[-1] if done else 'Starting...')
" 2>/dev/null)

    MINS=$((ELAPSED / 60)); SECS=$((ELAPSED % 60))
    printf "  [%02d:%02d]    %-20s  %s\n" "$MINS" "$SECS" "$STATUS" "$STEP"

    if [ "$STATUS" = "completed" ]; then
        echo ""
        if [ "$CONCLUSION" = "success" ]; then
            echo "================================================"
            echo "  ✓  BUILD SUCCEEDED!"
            echo "================================================"
            echo ""
            echo "  Downloading APK..."

            ARTIFACT_URL=$(_api "$API/actions/runs/$RUN_ID/artifacts" | python3 -c "
import sys, json
arts = json.load(sys.stdin).get('artifacts', [])
print(arts[0]['archive_download_url'] if arts else '')
" 2>/dev/null)

            if [ -n "$ARTIFACT_URL" ]; then
                mkdir -p apk_output
                curl -L -s \
                    -H "$AUTH_HEADER" \
                    -H "$ACCEPT_HEADER" \
                    -o apk_output/YouTubeConverter-APK.zip \
                    "$ARTIFACT_URL"

                unzip -o apk_output/YouTubeConverter-APK.zip -d apk_output/ > /dev/null 2>&1
                rm -f apk_output/YouTubeConverter-APK.zip

                echo ""
                echo "  APK saved to: apk_output/"
                ls -lh apk_output/*.apk 2>/dev/null || ls -lh apk_output/
                echo ""
                echo "  Install options:"
                echo ""
                echo "    A) USB (adb):"
                echo "       adb install apk_output/YouTubeConverter-debug.apk"
                echo ""
                echo "    B) Manual (no PC needed):"
                echo "       Transfer the .apk file to your Android phone"
                echo "       Go to Settings > Install unknown apps"
                echo "       Tap the APK file to install"
                echo "================================================"
            else
                echo "  Auto-download failed. Get the APK manually:"
                echo "  https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
            fi
        else
            echo "================================================"
            echo "  ✗  BUILD FAILED (result: $CONCLUSION)"
            echo "================================================"
            echo ""
            echo "  View full logs:"
            echo "  https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
        fi
        exit 0
    fi
done

echo ""
echo "Timed out after ${MAX_WAIT}s. Check build manually:"
echo "  https://github.com/$GITHUB_REPO/actions"
exit 1
