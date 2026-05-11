import os
import json
import threading
import time
import re
import subprocess

STATUS_FILE = '/data/data/com.youtube.converter/files/conversion_status.json'
DOWNLOAD_DIR = '/data/data/com.youtube.converter/files/downloads'

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)

_status_lock = threading.Lock()


def _read_status():
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _write_status(data):
    with _status_lock:
        tmp = STATUS_FILE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.replace(tmp, STATUS_FILE)


def update_status(file_id, updates):
    with _status_lock:
        data = _read_status()
        if file_id not in data:
            data[file_id] = {}
        data[file_id].update(updates)
        _write_status(data)


def get_status(file_id):
    data = _read_status()
    return data.get(file_id, {})


def get_all_status():
    return _read_status()


MP4_QUALITY_PRESETS = {
    '360p': {
        'name': '360p (Small)',
        'height': 360,
        'video_bitrate': '600k',
        'audio_bitrate': '128k',
        'description': '~25 MB per 5 min',
    },
    '480p': {
        'name': '480p (Medium)',
        'height': 480,
        'video_bitrate': '1000k',
        'audio_bitrate': '128k',
        'description': '~40 MB per 5 min',
    },
    '720p': {
        'name': '720p HD',
        'height': 720,
        'video_bitrate': '2500k',
        'audio_bitrate': '192k',
        'description': '~90 MB per 5 min',
    },
    '1080p': {
        'name': '1080p Full HD',
        'height': 1080,
        'video_bitrate': '5000k',
        'audio_bitrate': '192k',
        'description': '~180 MB per 5 min',
    },
}

MP3_QUALITY_PRESETS = {
    '128k': {
        'name': '128 kbps (Good)',
        'bitrate': '128k',
        'description': '~5 MB per 5 min',
    },
    '192k': {
        'name': '192 kbps (High)',
        'bitrate': '192k',
        'description': '~7 MB per 5 min',
    },
    '256k': {
        'name': '256 kbps (Very High)',
        'bitrate': '256k',
        'description': '~9 MB per 5 min',
    },
    '320k': {
        'name': '320 kbps (Maximum)',
        'bitrate': '320k',
        'description': '~12 MB per 5 min',
    },
}


def _sanitize_filename(name, max_len=60):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    return name[:max_len].strip()


def _find_ffmpeg():
    candidates = ['ffmpeg', '/data/data/com.youtube.converter/files/ffmpeg']
    for c in candidates:
        try:
            r = subprocess.run([c, '-version'], capture_output=True, timeout=5)
            if r.returncode == 0:
                return c
        except Exception:
            pass
    return None


DOWNLOAD_STRATEGIES = [
    {
        'name': 'Android Test Suite',
        'extractor_args': {'youtube': {'player_client': ['android_testsuite'], 'player_skip': ['configs', 'webpage', 'js']}},
        'http_headers': {'User-Agent': 'com.google.android.youtube/19.45.38 (Linux; U; Android 14; en_US)'},
    },
    {
        'name': 'Android Client',
        'extractor_args': {'youtube': {'player_client': ['android'], 'player_skip': ['configs', 'webpage']}},
        'http_headers': {'User-Agent': 'com.google.android.youtube/19.45.38 (Linux; U; Android 14; en_US)'},
    },
    {
        'name': 'iOS Client',
        'extractor_args': {'youtube': {'player_client': ['ios'], 'player_skip': ['configs', 'webpage']}},
        'http_headers': {'User-Agent': 'com.google.ios.youtube/19.45.4 (iPhone16,2; U; CPU iOS 18_1_1 like Mac OS X;)'},
    },
    {
        'name': 'TV Embedded',
        'extractor_args': {'youtube': {'player_client': ['tv_embedded'], 'player_skip': ['configs', 'webpage']}},
        'http_headers': {'User-Agent': 'Mozilla/5.0 (SMART-TV; Linux; Tizen 6.5) AppleWebKit/537.36 Chrome/94.0.4606.31 TV Safari/537.36'},
    },
]


def _do_download_convert(url, file_id, output_format, quality):
    import yt_dlp

    try:
        update_status(file_id, {
            'status': 'downloading',
            'progress': 'Starting download...',
            'url': url,
            'format': output_format,
            'quality': quality,
            'started_at': time.time(),
        })

        is_mp3 = output_format == 'mp3'
        temp_path = os.path.join(DOWNLOAD_DIR, f'{file_id}_temp.%(ext)s')
        temp_mp4 = os.path.join(DOWNLOAD_DIR, f'{file_id}_temp.mp4')

        if is_mp3:
            fmt_str = 'bestaudio/best'
        else:
            preset = MP4_QUALITY_PRESETS.get(quality, MP4_QUALITY_PRESETS['480p'])
            h = preset['height']
            fmt_str = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'

        base_opts = {
            'format': fmt_str,
            'merge_output_format': 'mp4',
            'outtmpl': temp_path,
            'nocheckcertificate': True,
            'retries': 6,
            'fragment_retries': 6,
            'quiet': True,
            'no_warnings': True,
        }

        last_error = None
        download_success = False
        video_title = 'video'

        for i, strategy in enumerate(DOWNLOAD_STRATEGIES):
            try:
                if i > 0:
                    update_status(file_id, {'progress': f'Retrying with {strategy["name"]} ({i+1}/{len(DOWNLOAD_STRATEGIES)})...'})
                    time.sleep(2 * i)

                opts = {**base_opts, **{'extractor_args': strategy['extractor_args'], 'http_headers': strategy['http_headers']}}

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info and info.get('title'):
                        video_title = _sanitize_filename(info['title'])

                if os.path.exists(temp_mp4) and os.path.getsize(temp_mp4) > 0:
                    download_success = True
                    break
                else:
                    found = None
                    for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                        p = os.path.join(DOWNLOAD_DIR, f'{file_id}_temp.{ext}')
                        if os.path.exists(p) and os.path.getsize(p) > 0:
                            found = p
                            break
                    if found:
                        os.rename(found, temp_mp4)
                        download_success = True
                        break

            except Exception as e:
                last_error = str(e)
                continue

        if not download_success:
            raise Exception(f'Download failed: {last_error or "All strategies exhausted"}')

        ffmpeg = _find_ffmpeg()

        if is_mp3:
            preset = MP3_QUALITY_PRESETS.get(quality, MP3_QUALITY_PRESETS['192k'])
            out_path = os.path.join(DOWNLOAD_DIR, f'{file_id}.mp3')
            update_status(file_id, {'status': 'converting', 'progress': f'Converting to MP3 ({preset["name"]})...'})

            if ffmpeg:
                cmd = [
                    ffmpeg, '-y', '-i', temp_mp4,
                    '-vn', '-acodec', 'libmp3lame',
                    '-b:a', preset['bitrate'],
                    '-ac', '2', out_path
                ]
                r = subprocess.run(cmd, capture_output=True, timeout=3600)
                if r.returncode != 0:
                    raise Exception(f'FFmpeg MP3 conversion failed: {r.stderr.decode()[:200]}')
            else:
                opts2 = {
                    'format': 'bestaudio/best',
                    'outtmpl': out_path.replace('.mp3', '.%(ext)s'),
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': preset['bitrate'].replace('k', '')}],
                    'quiet': True,
                }
                with yt_dlp.YoutubeDL(opts2) as ydl:
                    ydl.download([url])

        else:
            preset = MP4_QUALITY_PRESETS.get(quality, MP4_QUALITY_PRESETS['480p'])
            out_path = os.path.join(DOWNLOAD_DIR, f'{file_id}.mp4')
            update_status(file_id, {'status': 'converting', 'progress': f'Converting to MP4 {preset["name"]}...'})

            if ffmpeg:
                h = preset['height']
                cmd = [
                    ffmpeg, '-y', '-i', temp_mp4,
                    '-vf', f'scale=-2:{h}',
                    '-c:v', 'libx264', '-preset', 'fast',
                    '-b:v', preset['video_bitrate'],
                    '-c:a', 'aac', '-b:a', preset['audio_bitrate'],
                    '-movflags', '+faststart',
                    out_path
                ]
                r = subprocess.run(cmd, capture_output=True, timeout=3600)
                if r.returncode != 0:
                    os.rename(temp_mp4, out_path)
            else:
                os.rename(temp_mp4, out_path)

        if os.path.exists(temp_mp4):
            try:
                os.remove(temp_mp4)
            except Exception:
                pass

        file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        update_status(file_id, {
            'status': 'completed',
            'progress': 'Done!',
            'output_path': out_path,
            'video_title': video_title,
            'file_size': file_size,
            'completed_at': time.time(),
        })

    except Exception as e:
        for ext in ['mp4', 'webm', 'mkv', 'm4a']:
            p = os.path.join(DOWNLOAD_DIR, f'{file_id}_temp.{ext}')
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        update_status(file_id, {
            'status': 'failed',
            'progress': f'Error: {str(e)[:300]}',
        })


def start_conversion(url, file_id, output_format='mp4', quality='480p'):
    t = threading.Thread(target=_do_download_convert, args=(url, file_id, output_format, quality), daemon=True)
    t.start()
    return file_id


def search_youtube(query, max_results=10):
    import yt_dlp
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'socket_timeout': 30,
    }
    results = []
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f'ytsearch{max_results}:{query}', download=False)
            if info and 'entries' in info:
                for entry in info['entries']:
                    if not entry:
                        continue
                    vid_id = entry.get('id', '')
                    dur = entry.get('duration', 0)
                    results.append({
                        'id': vid_id,
                        'title': entry.get('title', 'Unknown'),
                        'url': f'https://www.youtube.com/watch?v={vid_id}',
                        'duration': f'{int(dur//60)}:{int(dur%60):02d}' if dur else 'Unknown',
                        'channel': entry.get('channel', entry.get('uploader', 'Unknown')),
                        'thumbnail': f'https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg',
                    })
    except Exception as e:
        return {'error': str(e)}
    return results


def get_video_info(url):
    import yt_dlp
    opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
            }
    except Exception as e:
        return {'error': str(e)}


def cleanup_old_files(max_age_hours=24):
    cutoff = time.time() - max_age_hours * 3600
    for f in os.listdir(DOWNLOAD_DIR):
        p = os.path.join(DOWNLOAD_DIR, f)
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except Exception:
            pass
