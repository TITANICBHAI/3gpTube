# YouTube Converter — Android App

A no-server Android app that downloads and converts YouTube videos to **MP4** (360p/480p/720p/1080p) or **MP3** directly on your Android phone using Python via Chaquopy.

## Features
- Download YouTube videos as MP4 or MP3
- Quality selection: 360p, 480p, 720p, 1080p / 128–320 kbps
- YouTube search built in
- Download history
- Share YouTube links directly to the app
- No server required — everything runs on-device

## How to Build the APK

### Option A — Automated via GitHub Actions (Recommended)

1. **Set up environment variables** in Replit Secrets:
   - `GITHUB_TOKEN` — your GitHub Personal Access Token (needs `repo` scope)
   - `GITHUB_REPO` — your repo in `username/reponame` format
   - `GITHUB_BRANCH` — branch to push to (default: `main`)

2. **Create the GitHub repo** at https://github.com/new (must be empty or initialized)

3. **Push the code:**
   ```bash
   ./push_to_github.sh
   ```

4. **Watch the build:**
   ```bash
   ./watch_build.sh
   ```
   The APK downloads automatically when the build finishes (~10-15 minutes).

5. **Install on your phone:**
   - Transfer `apk_output/YouTubeConverter-debug.apk` to your Android device
   - Enable "Install from unknown sources" in Settings
   - Open the APK to install

### Option B — Build in Android Studio

1. Clone the `android-app/` folder
2. Open it in Android Studio (File > Open)
3. Let Gradle sync
4. Build > Generate Signed APK (or Build > Build Bundle/APK > Build APK)

## Architecture

```
android-app/
├── app/src/main/
│   ├── java/com/youtube/converter/
│   │   ├── MainActivity.kt          # Entry point, bottom nav
│   │   ├── PythonManager.kt         # Chaquopy Python bridge
│   │   ├── ConverterViewModel.kt    # Download/convert state
│   │   └── ui/
│   │       ├── ConverterFragment.kt # Main convert screen
│   │       ├── SearchFragment.kt    # YouTube search
│   │       └── HistoryFragment.kt   # Past downloads
│   ├── python/
│   │   └── converter.py             # yt-dlp + FFmpeg logic
│   └── res/layout/                  # UI layouts
├── .github/workflows/build-apk.yml  # GitHub Actions CI
```

## Output Formats

| Format | Quality | Approx Size (5 min) |
|--------|---------|---------------------|
| MP4    | 360p    | ~25 MB              |
| MP4    | 480p    | ~40 MB              |
| MP4    | 720p HD | ~90 MB              |
| MP4    | 1080p   | ~180 MB             |
| MP3    | 128 kbps| ~5 MB               |
| MP3    | 192 kbps| ~7 MB               |
| MP3    | 256 kbps| ~9 MB               |
| MP3    | 320 kbps| ~12 MB              |
