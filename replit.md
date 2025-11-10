# YouTube to 3GP/MP3 Converter for Feature Phones

## Overview

This is a Flask-based web application that converts YouTube videos to feature phone-compatible formats (3GP video and MP3 audio). The application is specifically designed for users with older Nokia phones and low-bandwidth 2G/3G networks. It provides a simple, lightweight interface optimized for basic browsers and includes features like video search, playlist conversion, file splitting for large downloads, and optional cookie management for bypassing YouTube restrictions.

## Recent Changes

**November 10, 2025 - Subtitle Burning Feature (EXPERIMENTAL)**
- ✓ Implemented English subtitle burning capability using MoviePy for YouTube-style subtitle overlays
- ✓ Added download_subtitles() function to fetch English subtitles via yt-dlp (manual + auto-generated)
- ✓ Created burn_subtitles_moviepy() with memory-conscious settings for Render constraints (threads=1, ultrafast preset)
- ✓ Integrated subtitle burning into conversion pipeline with resource limits (45 min, 500MB max when enabled)
- ✓ Added UI checkboxes in index.html and 3gp.html with clear experimental warnings
- ✓ Installed ImageMagick and DejaVu fonts in dev environment
- ⚠️ Feature requires ImageMagick + fonts on deployment platform (works in dev, may fail gracefully in production)
- ✓ Implemented graceful degradation: subtitle burning failure continues normal conversion with status messages

**Earlier Changes**
- ✓ Implemented full playlist support with detection, confirmation page, and batch processing
- ✓ Fixed playlist URL detection to handle both pure playlist URLs and watch?v=...&list=... formats
- ✓ Configured unlimited processing time (DOWNLOAD_TIMEOUT = None, CONVERSION_TIMEOUT = None, MAX_VIDEO_DURATION = None)
- ✓ Implemented smart cleanup that only deletes completed files after 6 hours (processing files never expire)
- ✓ Installed FFmpeg system dependency for video/audio conversion
- ✓ Configured Flask workflow running on port 5000 with proper host binding (0.0.0.0)
- ✓ Added thread-safe JSON persistence for playlist status tracking

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask
- **Design Philosophy**: Minimal, feature-phone-optimized HTML/CSS
  - Inline CSS for simplicity and reduced HTTP requests
  - No JavaScript dependencies (works on basic browsers)
  - Low-resolution optimized layouts (max-width: 400px)
  - Cache-control headers to prevent stale content
  - Optional thumbnail loading to save bandwidth
- **User Interface Pattern**: Form-based workflows with server-side rendering
  - Status pages with auto-refresh meta tags (30-second intervals)
  - Simple navigation with button-style links
  - Progressive disclosure of conversion options

### Backend Architecture
- **Web Framework**: Flask 3.0.0
  - Session management with secret key (environment variable or generated)
  - After-request cache control for HTML responses
  - Template rendering for all user-facing pages
- **Download Engine**: yt-dlp library
  - Multiple download methods (7 fallback strategies mentioned in templates)
  - Cookie support for bypassing YouTube restrictions (optional)
  - Format selection and quality presets for 3GP and MP3
- **File Processing**: Server-side video/audio conversion
  - Subprocess-based FFmpeg operations (implied by conversion functionality)
  - Background processing with threading for long-running conversions
  - File splitting capability for large files (re-encoding each part)
  - **Subtitle Burning (EXPERIMENTAL)**: MoviePy-based subtitle overlay
    - Downloads English subtitles (manual or auto-generated) via yt-dlp
    - Burns subtitles into video with YouTube-style formatting (white text, black background)
    - Memory-optimized settings for Render constraints (threads=1, bufsize=2M)
    - Resource limits: max 45 minutes, 500MB file size when enabled
    - Requires ImageMagick and system fonts (DejaVu-Sans-Bold preferred)
    - Graceful degradation: continues normal conversion if subtitle burning fails
- **Status Tracking**: JSON-based status file system
  - File: `/tmp/conversion_status.json`
  - Tracks download/conversion progress
  - Manages file lifecycle and cleanup (6-hour retention)
  - History tracking (48-hour window)

### Data Storage
- **File Storage**: Temporary filesystem storage
  - Downloads folder: `/tmp/downloads`
  - Cookies folder: `/tmp/cookies`
  - Ephemeral storage with automatic cleanup
  - File retention: 6 hours after conversion
  - History retention: 48 hours
- **State Management**: JSON file for conversion status
  - No persistent database
  - In-memory session state via Flask sessions
  - Stateless design suitable for cloud/container deployment
- **File Identification**: Hash-based file IDs
  - Uses hashlib for generating unique file identifiers
  - Enables file deduplication and retrieval

### Processing Pipeline
- **Conversion Workflow**:
  1. URL submission (single video or playlist)
  2. Format selection (3GP video or MP3 audio)
  3. Quality preset selection
  4. Background download and conversion
  5. Status polling with auto-refresh
  6. File delivery via send_file
- **Playlist Handling**:
  - Playlist detection and confirmation step
  - Sequential video processing
  - Progress tracking per video and overall
  - Partial success handling (some videos may fail)
- **File Splitting**:
  - Post-download splitting for large files
  - Configurable number of parts (2-50)
  - Re-encoding each part for compatibility
  - Command-line instructions for rejoining parts

### Quality Presets
- **3GP Video Presets**: Multiple quality levels for different network conditions
  - Auto mode (recommended low quality)
  - Resolution: 176x144 mentioned as default
  - Configurable via video_quality parameter
- **MP3 Audio Presets**: Bitrate-based quality selection
  - Auto mode defaults to 128kbps
  - Multiple preset options for different file sizes
  - Configurable via mp3_quality parameter

## External Dependencies

### Third-Party Services
- **YouTube**: Primary video source
  - Video and playlist metadata extraction
  - Content download via yt-dlp
  - Search functionality
  - Optional cookie-based authentication
- **yt-dlp Library**: YouTube download engine
  - Version: 2024.11.4
  - Handles video extraction, format selection, and download
  - Manages YouTube API interactions and format negotiation

### Required System Tools
- **FFmpeg**: Video/audio conversion
  - Used for format conversion (3GP, MP3)
  - File splitting and re-encoding
  - Should be available in system PATH
- **ImageMagick** (Optional - for subtitle burning): Text rendering for MoviePy
  - Required for subtitle burning feature
  - Installed in dev environment via Nix (imagemagick, dejavu_fonts)
  - Must be provisioned separately for Render/production deployment
  - Subtitle feature fails gracefully if not available

### Python Dependencies
- **Flask 3.0.0**: Web framework
- **yt-dlp 2024.11.4**: YouTube downloader
- **gunicorn 21.2.0**: WSGI HTTP server for production deployment
- **moviepy 1.0.3**: Video editing and subtitle burning (experimental feature)

### Environment Variables
- **SESSION_SECRET**: Flask session encryption key (optional, auto-generated if missing)

### Cookie Management (Optional)
- **Purpose**: Bypass YouTube restrictions and rate limits
- **Format**: Netscape cookies.txt format
- **Storage**: `/tmp/cookies/youtube_cookies.txt`
- **Validation**: Cookie format and YouTube domain checking
- **Use Case**: Cloud hosting with IP-based rate limiting, sign-in required errors

### Deployment Considerations
- Designed for cloud/container deployment (ephemeral storage in /tmp)
- No persistent database required
- Suitable for Replit, Heroku, or similar platforms
- Requires FFmpeg installation on host system
- File cleanup mechanism needed for long-running instances
- **For Subtitle Burning on Render**: Must install ImageMagick and fonts in build command:
  ```
  apt-get update && apt-get install -y imagemagick fonts-dejavu-core
  ```
  - Feature will fail gracefully without these dependencies
  - Users will receive clear error messages in status updates