#!/usr/bin/env python3
"""
watch_build.py — Push changed files to GitHub via API, then watch the
GitHub Actions build live and print all errors on failure.

Usage:
    python watch_build.py [optional commit message]
    python watch_build.py --watch-only          # skip push, just watch latest run
    python watch_build.py --logs-only           # print logs from latest run and exit
"""
import os, sys, json, time, datetime, hashlib, base64, urllib.request, urllib.error, http.client, urllib.parse

# ── Config ─────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
REPO  = os.environ.get("GITHUB_REPO", "TITANICBHAI/3gpTube")
BRANCH = "main"
API   = f"https://api.github.com/repos/{REPO}"
H     = {
    "Authorization": f"token {TOKEN}",
    "Accept":        "application/vnd.github.v3+json",
    "Content-Type":  "application/json",
    "User-Agent":    "replit-watch-build",
}

# Files to track for changes (relative to project root).
# Edit this list to add/remove files the script will auto-push.
TRACK = [
    ".github/workflows/build-apk.yml",
    "android-app/app/build.gradle",
    "android-app/build.gradle",
    "android-app/settings.gradle",
    "android-app/gradle.properties",
    "android-app/gradle/wrapper/gradle-wrapper.properties",
    "android-app/app/src/main/AndroidManifest.xml",
    "android-app/app/src/main/java/com/youtube/converter/MainActivity.kt",
    "android-app/app/src/main/java/com/youtube/converter/ConverterViewModel.kt",
    "android-app/app/src/main/java/com/youtube/converter/PythonManager.kt",
    "android-app/app/src/main/java/com/youtube/converter/ui/SearchFragment.kt",
    "android-app/app/src/main/java/com/youtube/converter/ui/ConverterFragment.kt",
    "android-app/app/src/main/java/com/youtube/converter/ui/HistoryFragment.kt",
    "android-app/app/src/main/java/com/youtube/converter/ui/HistoryAdapter.kt",
    "android-app/app/src/main/java/com/youtube/converter/ui/SearchResultAdapter.kt",
]

BAR = "=" * 58

# ── Helpers ─────────────────────────────────────────────────────────────────
def gh(method, path, data=None, raw=False):
    url = path if path.startswith("http") else f"{API}/{path}"
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(url, data=body, headers=H, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            content = r.read()
            if raw:
                return content
            if not content.strip():
                return {}          # 204 No Content or empty body
            return json.loads(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        print(f"  HTTP {e.code} on {method} {path}: {body}")
        return None

def get_log_text(job_id):
    parsed = urllib.parse.urlparse(f"{API}/actions/jobs/{job_id}/logs")
    conn = http.client.HTTPSConnection(parsed.netloc)
    conn.request("GET", parsed.path, headers={k: v for k,v in H.items() if k != "Content-Type"})
    resp = conn.getresponse()
    location = resp.getheader("Location", "")
    conn.close()
    if not location:
        return ""
    req2 = urllib.request.Request(location, headers={"User-Agent": "replit-watch-build"})
    try:
        with urllib.request.urlopen(req2) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"(log fetch error: {e})"

def strip_ts(line):
    # Remove GitHub Actions timestamp prefix e.g. "2026-05-11T20:31:47.0462612Z "
    if len(line) > 29 and line[10] == 'T' and 'Z ' in line[:35]:
        return line[line.find('Z ')+2:]
    return line

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def sha256_b64(content_bytes):
    return hashlib.sha256(content_bytes).hexdigest()

# ── Push changed files ───────────────────────────────────────────────────────
def push_changes(commit_msg):
    print(f"\n[1/3] Comparing local files with {REPO}/{BRANCH}...")

    branch_data = gh("GET", f"git/refs/heads/{BRANCH}")
    if not branch_data:
        print("  ERROR: Could not fetch branch ref. Check GITHUB_PERSONAL_ACCESS_TOKEN.")
        return None
    base_commit_sha = branch_data["object"]["sha"]
    base_tree_sha   = gh("GET", f"git/commits/{base_commit_sha}")["tree"]["sha"]

    # Fetch remote file SHAs in one call (tree recursive)
    tree_data = gh("GET", f"git/trees/{base_tree_sha}?recursive=1") or {}
    remote_sha = {item["path"]: item.get("sha","") for item in tree_data.get("tree", [])}

    changed = []
    for path in TRACK:
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            content_bytes = f.read()
        # GitHub blob SHA = sha1("blob {len}\0{content}")
        import hashlib as _hl
        h = _hl.sha1()
        h.update(f"blob {len(content_bytes)}\0".encode())
        h.update(content_bytes)
        git_sha = h.hexdigest()
        if remote_sha.get(path) != git_sha:
            changed.append((path, content_bytes))

    if not changed:
        print(f"  No local changes detected in tracked files.")
        print(f"  Triggering workflow_dispatch instead...")
        gh("POST", f"actions/workflows/build-apk.yml/dispatches", {"ref": BRANCH})
        return int(time.time())

    print(f"  {len(changed)} file(s) changed:")
    for path, _ in changed:
        print(f"    + {path}")

    tree_entries = []
    for path, content_bytes in changed:
        # detect binary vs text
        try:
            content_str = content_bytes.decode("utf-8")
            blob = gh("POST", "git/blobs", {"content": content_str, "encoding": "utf-8"})
        except UnicodeDecodeError:
            blob = gh("POST", "git/blobs", {"content": base64.b64encode(content_bytes).decode(), "encoding": "base64"})
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

    new_tree   = gh("POST", "git/trees", {"base_tree": base_tree_sha, "tree": tree_entries})
    new_commit = gh("POST", "git/commits", {
        "message": commit_msg,
        "tree":    new_tree["sha"],
        "parents": [base_commit_sha],
        "author":  {"name": "Replit Build Bot", "email": "bot@replit.com"},
    })
    result = gh("PATCH", f"git/refs/heads/{BRANCH}", {"sha": new_commit["sha"], "force": True})
    push_ts = int(time.time())
    print(f"\n  Pushed commit {new_commit['sha'][:12]}  ({datetime.datetime.utcnow().strftime('%H:%M UTC')})")
    print(f"  Actions: https://github.com/{REPO}/actions")
    return push_ts

# ── Wait for new run ─────────────────────────────────────────────────────────
def wait_for_run(push_ts, skip_run_id=None):
    print(f"\n[2/3] Waiting for GitHub Actions to pick up the build...")
    for attempt in range(30):
        time.sleep(10)
        data = gh("GET", f"actions/runs?per_page=10&branch={BRANCH}") or {}
        for r in data.get("workflow_runs", []):
            if r["id"] == skip_run_id:
                continue
            try:
                t  = datetime.datetime.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                ts = (t - datetime.datetime(1970, 1, 1)).total_seconds()
            except Exception:
                continue
            if ts >= push_ts - 90:
                print(f"  Run #{r['id']} found — {r['html_url']}")
                return r["id"]
        m, s = divmod((attempt+1)*10, 60)
        print(f"  [{m:02d}:{s:02d}] Waiting for run...")
    # fallback: latest run
    data = gh("GET", "actions/runs?per_page=1") or {}
    runs = data.get("workflow_runs", [])
    if runs:
        r = runs[0]
        print(f"  Fallback: using latest run #{r['id']}")
        return r["id"]
    return None

# ── Watch build live ──────────────────────────────────────────────────────────
def watch_run(run_id):
    print(f"\n[3/3] Watching build #{run_id} live...")
    print(f"      https://github.com/{REPO}/actions/runs/{run_id}\n")
    print(f"  {'TIME':<9}  {'STATUS':<20}  CURRENT STEP")
    print(f"  {'─'*9}  {'─'*20}  {'─'*44}")

    elapsed   = 0
    last_step = ""

    while elapsed < 3600:
        time.sleep(15)
        elapsed += 15

        run  = gh("GET", f"actions/runs/{run_id}") or {}
        status     = run.get("status", "")
        conclusion = run.get("conclusion", "")

        jobs_data = gh("GET", f"actions/runs/{run_id}/jobs") or {}
        jobs = jobs_data.get("jobs", [])
        step = "Queued"
        if jobs:
            steps  = jobs[0].get("steps", [])
            active = [s["name"] for s in steps if s.get("status") == "in_progress"]
            done   = [s["name"] for s in steps if s.get("status") == "completed"]
            step   = active[0] if active else (done[-1] if done else "Starting...")

        m, s = divmod(elapsed, 60)
        if step != last_step or elapsed % 60 == 0:
            print(f"  [{m:02d}:{s:02d}]    {status:<20}  {step}")
            last_step = step

        if status == "completed":
            print()
            return conclusion, jobs

    return "timeout", []

# ── Handle result ─────────────────────────────────────────────────────────────
def handle_success(run_id):
    print(BAR)
    print("  BUILD SUCCEEDED!")
    print(BAR)
    arts = (gh("GET", f"actions/runs/{run_id}/artifacts") or {}).get("artifacts", [])
    for a in arts:
        kb = a["size_in_bytes"] // 1024
        print(f"  Artifact : {a['name']}  ({kb} KB)")
        # Download — follow redirect without auth (Azure Blob rejects Bearer)
        try:
            dl_url = a["archive_download_url"]
            out_dir = "apk_output"
            os.makedirs(out_dir, exist_ok=True)
            zip_path = f"{out_dir}/{a['name']}.zip"

            # Step 1: get redirect URL from GitHub (with auth)
            req1 = urllib.request.Request(dl_url, headers=H, method="GET")
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
            # Don't follow automatically — we need to strip auth on redirect
            no_redirect = urllib.request.build_opener()
            no_redirect.handlers = [h for h in no_redirect.handlers
                                     if not isinstance(h, urllib.request.HTTPRedirectHandler)]
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            nr_opener = urllib.request.build_opener(NoRedirect())
            try:
                nr_opener.open(req1)
                redirect_url = None
            except urllib.error.HTTPError as e:
                redirect_url = e.headers.get("Location")

            if not redirect_url:
                raise Exception("no redirect URL from GitHub")

            # Step 2: download from Azure without auth header
            req2 = urllib.request.Request(redirect_url, headers={"User-Agent": "replit-watch-build"})
            with urllib.request.urlopen(req2) as r:
                with open(zip_path, "wb") as f:
                    f.write(r.read())

            import zipfile
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(out_dir)
            os.remove(zip_path)
            apks = [x for x in os.listdir(out_dir) if x.endswith(".apk")]
            for apk in apks:
                sz = os.path.getsize(f"{out_dir}/{apk}") // (1024*1024)
                print(f"  Saved    : {out_dir}/{apk}  ({sz} MB)")
        except Exception as e:
            print(f"  (auto-download failed: {e})")
            print(f"  Download : https://github.com/{REPO}/actions/runs/{run_id}")
    print(BAR)
    if os.path.exists("apk_output"):
        print("\n  Install via ADB:")
        print("    adb install apk_output/*.apk")
    print(f"\n  Actions page: https://github.com/{REPO}/actions/runs/{run_id}")

def handle_failure(run_id, jobs):
    print(BAR)
    print("  BUILD FAILED")
    print(BAR)

    if not jobs:
        print(f"  Full log: https://github.com/{REPO}/actions/runs/{run_id}")
        return

    failed = [j for j in jobs if j.get("conclusion") == "failure"]
    job    = failed[0] if failed else jobs[0]
    log    = get_log_text(job["id"])

    if not log:
        print("  (could not fetch log)")
        print(f"  Full log: https://github.com/{REPO}/actions/runs/{run_id}")
        return

    lines = log.splitlines()
    print(f"\n  Log has {len(lines)} lines total. Extracting errors...\n")

    # Kotlin compiler errors
    kotlin_errors = []
    for line in lines:
        s = strip_ts(line)
        if any(marker in s for marker in [
            "e: file://", "Unresolved reference", "Type inference failed",
            "Type mismatch", "None of the following candidates",
            "Overload resolution ambiguity", "Val cannot be reassigned",
            "Cannot access", "Expecting an expression",
        ]):
            kotlin_errors.append(s)

    # General build errors
    general_errors = set()
    shown = []
    for i, line in enumerate(lines):
        s = strip_ts(line)
        if any(x in s for x in [
            "BUILD FAILED", "What went wrong:", "Execution failed for task",
            "Could not resolve", "Could not find", "> Task :", "error:",
            "Exception in thread", ": error",
        ]):
            for j in range(max(0,i-1), min(len(lines),i+6)):
                if j not in general_errors:
                    general_errors.add(j)
                    shown.append((j, strip_ts(lines[j])))

    if kotlin_errors:
        print("  ── Kotlin Compiler Errors ──────────────────────────────")
        for e in kotlin_errors:
            print(f"    {e}")

    if shown:
        print("\n  ── Build Errors ────────────────────────────────────────")
        prev = -1
        for idx, s in sorted(shown, key=lambda x: x[0]):
            if idx != prev + 1 and prev != -1:
                print("    ...")
            print(f"    {s}")
            prev = idx

    print(f"\n  Full log: https://github.com/{REPO}/actions/runs/{run_id}")
    print(BAR)

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    if not TOKEN:
        print("ERROR: GITHUB_PERSONAL_ACCESS_TOKEN not set in environment.")
        sys.exit(1)

    args = sys.argv[1:]
    watch_only = "--watch-only" in args
    logs_only  = "--logs-only"  in args
    commit_msg = next((a for a in args if not a.startswith("--")),
                      f"build: update Android app {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    print(BAR)
    print("  GitHub Actions Build Monitor")
    print(f"  Repo  : {REPO}")
    print(f"  Branch: {BRANCH}")
    print(BAR)

    if logs_only:
        # Just print errors from the latest run and exit
        data = gh("GET", "actions/runs?per_page=1") or {}
        runs = data.get("workflow_runs", [])
        if not runs:
            print("No runs found.")
            sys.exit(1)
        r = runs[0]
        run_id = r["id"]
        print(f"\nLatest run #{run_id}  status={r['status']}  conclusion={r.get('conclusion','')}")
        jobs_data = gh("GET", f"actions/runs/{run_id}/jobs") or {}
        jobs = jobs_data.get("jobs", [])
        if r.get("conclusion") == "success":
            handle_success(run_id)
        else:
            handle_failure(run_id, jobs)
        sys.exit(0)

    if watch_only:
        # Find latest run, watch it
        data = gh("GET", "actions/runs?per_page=1") or {}
        runs = data.get("workflow_runs", [])
        if not runs:
            print("No runs found.")
            sys.exit(1)
        run_id = runs[0]["id"]
        conclusion, jobs = watch_run(run_id)
    else:
        push_ts = push_changes(commit_msg)
        if push_ts is None:
            sys.exit(1)
        run_id = wait_for_run(push_ts)
        if not run_id:
            print("  Could not find workflow run. Check https://github.com/{REPO}/actions")
            sys.exit(1)
        conclusion, jobs = watch_run(run_id)

    if conclusion == "success":
        handle_success(run_id)
        sys.exit(0)
    else:
        handle_failure(run_id, jobs)
        sys.exit(1)

if __name__ == "__main__":
    main()
