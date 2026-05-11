#!/bin/bash
set -e

echo "================================================"
echo "   YouTube Converter — Build Android APK"
echo "================================================"
echo ""

# ── Resolve token (support both secret names) ────────
GITHUB_TOKEN="${GITHUB_PERSONAL_ACCESS_TOKEN:-$GITHUB_TOKEN}"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_PERSONAL_ACCESS_TOKEN is not set."
    echo ""
    echo "  Add it to Replit Secrets as GITHUB_PERSONAL_ACCESS_TOKEN"
    echo "  (needs 'repo' scope from https://github.com/settings/tokens)"
    exit 1
fi

# ── Hardcoded repo ───────────────────────────────────
GITHUB_REPO="${GITHUB_REPO:-TITANICBHAI/3gpTube}"
BRANCH="${GITHUB_BRANCH:-main}"
COMMIT_MSG="${1:-"build: update Android app $(date '+%Y-%m-%d %H:%M:%S')"}"
API="https://api.github.com/repos/$GITHUB_REPO"
AUTH_HEADER="Authorization: token $GITHUB_TOKEN"
ACCEPT_HEADER="Accept: application/vnd.github.v3+json"

_api() { curl -s -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" "$@"; }

echo "  Repo  : $GITHUB_REPO"
echo "  Branch: $BRANCH"
echo ""

# ── Step 1: Push to GitHub ───────────────────────────
echo "[1/3] Pushing code to GitHub ($GITHUB_REPO)..."
echo ""

REMOTE_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"
if ! git remote get-url origin &>/dev/null 2>&1; then
    git remote add origin "$REMOTE_URL"
else
    git remote set-url origin "$REMOTE_URL"
fi

git config user.email "build-bot@replit.com" 2>/dev/null || true
git config user.name  "Replit Build Bot"     2>/dev/null || true

git add -A

if git diff --cached --quiet; then
    echo "  Nothing new to commit — adding trigger commit..."
    git commit --allow-empty -m "ci: trigger APK build $(date '+%Y-%m-%d %H:%M:%S')"
else
    git commit -m "$COMMIT_MSG"
fi

git push -u origin "$BRANCH" --force 2>&1
PUSH_TIME=$(date +%s)
echo ""
echo "  Pushed at $(date '+%H:%M:%S')"
echo "  Actions: https://github.com/$GITHUB_REPO/actions"
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
            echo "  BUILD SUCCEEDED!"
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
                echo "    B) Manual:"
                echo "       Transfer the .apk to your Android phone"
                echo "       Settings > Install unknown apps > tap the APK"
                echo "================================================"
            else
                echo "  Get APK manually from:"
                echo "  https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
            fi
        else
            echo "================================================"
            echo "  BUILD FAILED (result: $CONCLUSION)"
            echo "================================================"
            echo ""

            # Print last 50 lines of logs for the failed job
            echo "  Fetching failure logs..."
            JOB_ID=$(_api "$API/actions/runs/$RUN_ID/jobs" | python3 -c "
import sys, json
jobs = json.load(sys.stdin).get('jobs', [])
failed = [j for j in jobs if j.get('conclusion') == 'failure']
print(failed[0]['id'] if failed else (jobs[0]['id'] if jobs else ''))
" 2>/dev/null)

            if [ -n "$JOB_ID" ]; then
                echo ""
                echo "  --- Last 60 lines of build log ---"
                _api "$API/actions/jobs/$JOB_ID/logs" | tail -60
                echo "  --- End of log ---"
            fi

            echo ""
            echo "  Full logs: https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
        fi
        exit 0
    fi
done

echo ""
echo "Timed out after ${MAX_WAIT}s. Check build manually:"
echo "  https://github.com/$GITHUB_REPO/actions"
exit 1
