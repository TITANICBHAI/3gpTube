#!/bin/bash

echo "================================"
echo "  Watching GitHub Actions Build"
echo "================================"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN not set."
    exit 1
fi

if [ -z "$GITHUB_REPO" ]; then
    echo "ERROR: GITHUB_REPO not set. Example: youruser/youtube-converter-android"
    exit 1
fi

API="https://api.github.com/repos/$GITHUB_REPO"
HEADERS=(-H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json")

echo "Waiting for workflow run to start..."
sleep 5

MAX_WAIT=1800
ELAPSED=0
POLL_INTERVAL=15

while [ $ELAPSED -lt $MAX_WAIT ]; do
    RESPONSE=$(curl -s "${HEADERS[@]}" "$API/actions/runs?per_page=1&event=push")
    RUN_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; runs=json.load(sys.stdin).get('workflow_runs',[]); print(runs[0]['id'] if runs else '')" 2>/dev/null)
    STATUS=$(echo "$RESPONSE"  | python3 -c "import sys,json; runs=json.load(sys.stdin).get('workflow_runs',[]); print(runs[0]['status'] if runs else '')" 2>/dev/null)
    CONCLUSION=$(echo "$RESPONSE" | python3 -c "import sys,json; runs=json.load(sys.stdin).get('workflow_runs',[]); print(runs[0].get('conclusion','') if runs else '')" 2>/dev/null)

    if [ -z "$RUN_ID" ]; then
        echo "[${ELAPSED}s] No workflow run found yet, retrying..."
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        continue
    fi

    JOBS=$(curl -s "${HEADERS[@]}" "$API/actions/runs/$RUN_ID/jobs")
    STEP=$(echo "$JOBS" | python3 -c "
import sys,json
data=json.load(sys.stdin)
jobs=data.get('jobs',[])
if jobs:
    steps=[s for s in jobs[0].get('steps',[]) if s.get('status')=='in_progress']
    if steps:
        print(steps[0]['name'])
    else:
        completed=[s for s in jobs[0].get('steps',[]) if s.get('status')=='completed']
        print(completed[-1]['name'] if completed else 'Starting...')
else:
    print('Queued...')
" 2>/dev/null)

    echo "[${ELAPSED}s] Status: $STATUS | Step: $STEP"

    if [ "$STATUS" = "completed" ]; then
        echo ""
        if [ "$CONCLUSION" = "success" ]; then
            echo "BUILD SUCCEEDED!"
            echo ""
            echo "Downloading APK info..."

            ARTIFACTS=$(curl -s "${HEADERS[@]}" "$API/actions/runs/$RUN_ID/artifacts")
            ARTIFACT_URL=$(echo "$ARTIFACTS" | python3 -c "
import sys,json
data=json.load(sys.stdin)
arts=data.get('artifacts',[])
if arts:
    print(arts[0].get('archive_download_url',''))
" 2>/dev/null)

            if [ -n "$ARTIFACT_URL" ]; then
                echo "Downloading APK (this saves as a zip containing the APK)..."
                curl -L -o YouTubeConverter-APK.zip "${HEADERS[@]}" "$ARTIFACT_URL"
                if [ -f YouTubeConverter-APK.zip ]; then
                    unzip -o YouTubeConverter-APK.zip -d ./apk_output/ 2>/dev/null
                    echo ""
                    echo "================================"
                    echo "APK downloaded to: ./apk_output/"
                    ls -lh ./apk_output/ 2>/dev/null
                    echo ""
                    echo "Install on your Android device:"
                    echo "  adb install ./apk_output/YouTubeConverter-debug.apk"
                    echo "  Or copy to your phone and install manually."
                    echo "================================"
                fi
            else
                echo "APK artifact URL not found. Download manually from:"
                echo "  https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
            fi
        else
            echo "BUILD FAILED (conclusion: $CONCLUSION)"
            echo ""
            echo "View logs at:"
            echo "  https://github.com/$GITHUB_REPO/actions/runs/$RUN_ID"
        fi
        exit 0
    fi

    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo "Timed out waiting for build. Check manually:"
echo "  https://github.com/$GITHUB_REPO/actions"
exit 1
