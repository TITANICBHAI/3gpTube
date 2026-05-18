import os
import sys
import threading
import json
import time
import re
import subprocess
import hashlib
import secrets
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_DIR = '/data/data/com.youtube.converter/files'
DOWNLOAD_FOLDER = os.path.join(APP_DIR, 'downloads')
STATUS_FILE = os.path.join(APP_DIR, 'conversion_status.json')
TEMPLATES_DIR = os.path.join(APP_DIR, 'templates')

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

status_lock = threading.Lock()


def _copy_templates():
    src = os.path.join(os.path.dirname(__file__), 'templates')
    if os.path.isdir(src):
        for fname in os.listdir(src):
            src_file = os.path.join(src, fname)
            dst_file = os.path.join(TEMPLATES_DIR, fname)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
        logger.info(f"Templates copied from {src} to {TEMPLATES_DIR}")
    else:
        logger.warning(f"Templates source dir not found: {src}")


def _read_status():
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _write_status(data):
    with status_lock:
        tmp = STATUS_FILE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.replace(tmp, STATUS_FILE)


def update_status(file_id, updates):
    with status_lock:
        data = _read_status()
        if file_id not in data:
            data[file_id] = {}
        data[file_id].update(updates)
        _write_status(data)


def get_status(file_id=None):
    data = _read_status()
    if file_id:
        return data.get(file_id, {})
    return data


def generate_file_id(url):
    timestamp = str(int(time.time() * 1000))
    return hashlib.md5(f"{url}_{timestamp}".encode()).hexdigest()[:16]


def sanitize_filename(name, max_len=60):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    return name[:max_len].strip()


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

MP3_PRESETS = {
    'medium': {'name': '128 kbps (Good Quality)', 'bitrate': '128k', 'description': '~5 MB per 5 min'},
    'high': {'name': '192 kbps (High Quality)', 'bitrate': '192k', 'description': '~7 MB per 5 min'},
    'veryhigh': {'name': '256 kbps (Very High Quality)', 'bitrate': '256k', 'description': '~9 MB per 5 min'},
    'extreme': {'name': '320 kbps (Maximum Quality)', 'bitrate': '320k', 'description': '~12 MB per 5 min'},
}

VIDEO_PRESETS = {
    'ultralow': {'name': 'Ultra Low (2G Networks)', 'video_bitrate': '150k', 'audio_bitrate': '64k', 'fps': '10', 'description': '~2 MB per 5 min'},
    'low': {'name': 'Low (Recommended for Feature Phones)', 'video_bitrate': '200k', 'audio_bitrate': '96k', 'fps': '12', 'description': '~3 MB per 5 min'},
    'medium': {'name': 'Medium (Better Quality)', 'video_bitrate': '300k', 'audio_bitrate': '128k', 'fps': '15', 'description': '~4 MB per 5 min'},
    'high': {'name': 'High (Best Quality)', 'video_bitrate': '400k', 'audio_bitrate': '192k', 'fps': '18', 'description': '~5 MB per 5 min'},
}

MP4_QUALITY_PRESETS = {
    '360p': {'name': '360p (Small)', 'height': 360, 'video_bitrate': '600k', 'audio_bitrate': '128k', 'description': '~25 MB per 5 min'},
    '480p': {'name': '480p (Medium)', 'height': 480, 'video_bitrate': '1000k', 'audio_bitrate': '128k', 'description': '~40 MB per 5 min'},
    '720p': {'name': '720p HD', 'height': 720, 'video_bitrate': '2500k', 'audio_bitrate': '192k', 'description': '~90 MB per 5 min'},
    '1080p': {'name': '1080p Full HD', 'height': 1080, 'video_bitrate': '5000k', 'audio_bitrate': '192k', 'description': '~180 MB per 5 min'},
}

MAX_HOURS = 24


def _find_ffmpeg():
    candidates = [
        os.path.join(APP_DIR, 'ffmpeg'),
        '/data/local/tmp/ffmpeg',
        'ffmpeg',
    ]
    for c in candidates:
        try:
            r = subprocess.run([c, '-version'], capture_output=True, timeout=5)
            if r.returncode == 0:
                return c
        except Exception:
            pass
    return None


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
        is_3gp = output_format == '3gp'
        temp_path = os.path.join(DOWNLOAD_FOLDER, f'{file_id}_temp.%(ext)s')
        temp_mp4 = os.path.join(DOWNLOAD_FOLDER, f'{file_id}_temp.mp4')

        if is_mp3:
            fmt_str = 'bestaudio/best'
        elif is_3gp:
            fmt_str = 'worst[ext=mp4]/worst/best[height<=240]/best'
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

                opts = {**base_opts, 'extractor_args': strategy['extractor_args'], 'http_headers': strategy['http_headers']}

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info and info.get('title'):
                        video_title = sanitize_filename(info['title'])

                if os.path.exists(temp_mp4) and os.path.getsize(temp_mp4) > 0:
                    download_success = True
                    break
                else:
                    found = None
                    for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                        p = os.path.join(DOWNLOAD_FOLDER, f'{file_id}_temp.{ext}')
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
            preset = MP3_PRESETS.get(quality, MP3_PRESETS['high'])
            out_path = os.path.join(DOWNLOAD_FOLDER, f'{file_id}.mp3')
            update_status(file_id, {'status': 'converting', 'progress': f'Converting to MP3 ({preset["name"]})...'})
            if ffmpeg:
                cmd = [ffmpeg, '-y', '-i', temp_mp4, '-vn', '-acodec', 'libmp3lame', '-b:a', preset['bitrate'], '-ac', '2', out_path]
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

        elif is_3gp:
            preset = VIDEO_PRESETS.get(quality, VIDEO_PRESETS['low'])
            out_path = os.path.join(DOWNLOAD_FOLDER, f'{file_id}.3gp')
            update_status(file_id, {'status': 'converting', 'progress': f'Converting to 3GP ({preset["name"]})...'})
            if ffmpeg:
                cmd = [
                    ffmpeg, '-y', '-i', temp_mp4,
                    '-vcodec', 'h263', '-s', '176x144',
                    '-r', preset['fps'],
                    '-b:v', preset['video_bitrate'],
                    '-acodec', 'aac',
                    '-b:a', preset['audio_bitrate'],
                    '-ar', '8000', '-ac', '1',
                    '-f', '3gp', out_path
                ]
                r = subprocess.run(cmd, capture_output=True, timeout=3600)
                if r.returncode != 0:
                    os.rename(temp_mp4, out_path.replace('.3gp', '.mp4'))
                    out_path = out_path.replace('.3gp', '.mp4')
            else:
                os.rename(temp_mp4, out_path.replace('.3gp', '.mp4'))
                out_path = out_path.replace('.3gp', '.mp4')

        else:
            preset = MP4_QUALITY_PRESETS.get(quality, MP4_QUALITY_PRESETS['480p'])
            out_path = os.path.join(DOWNLOAD_FOLDER, f'{file_id}.mp4')
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
            p = os.path.join(DOWNLOAD_FOLDER, f'{file_id}_temp.{ext}')
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        update_status(file_id, {
            'status': 'failed',
            'progress': f'Error: {str(e)[:300]}',
        })


def search_youtube(query, max_results=10):
    import yt_dlp
    opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'socket_timeout': 30}
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
                        'upload_date': entry.get('upload_date', ''),
                        'views': entry.get('view_count', ''),
                    })
    except Exception as e:
        return {'error': str(e)}
    return results


def _make_app():
    from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

    app = Flask(__name__, template_folder=TEMPLATES_DIR)
    app.secret_key = secrets.token_hex(32)

    def common_ctx():
        return {
            'video_presets': VIDEO_PRESETS,
            'mp3_presets': MP3_PRESETS,
            'mp4_quality_presets': MP4_QUALITY_PRESETS,
            'max_hours': MAX_HOURS,
            'has_cookies': False,
        }

    @app.route('/')
    def index():
        ctx = common_ctx()
        url = request.args.get('url', '')
        ctx['prefill_url'] = url
        return render_template('index.html', **ctx)

    @app.route('/mp3')
    def mp3_page():
        return render_template('mp3.html', **common_ctx())

    @app.route('/3gp')
    def gp3_page():
        return render_template('3gp.html', **common_ctx())

    @app.route('/convert', methods=['POST'])
    def convert():
        url = request.form.get('url', '').strip()
        output_format = request.form.get('format', '3gp')
        quality = request.form.get('video_quality') or request.form.get('mp3_quality') or request.form.get('quality', 'auto')

        if quality == 'auto':
            quality = 'low' if output_format == '3gp' else ('medium' if output_format == 'mp3' else '480p')

        if not url:
            return redirect(url_for('index'))

        file_id = generate_file_id(url)
        update_status(file_id, {'status': 'queued', 'url': url, 'format': output_format, 'quality': quality})

        t = threading.Thread(target=_do_download_convert, args=(url, file_id, output_format, quality), daemon=True)
        t.start()

        return redirect(f'/status_page/{file_id}')

    @app.route('/status_page/<file_id>')
    def status_page(file_id):
        file_status = get_status(file_id)
        ctx = common_ctx()
        ctx['file_id'] = file_id
        ctx['file_status'] = file_status
        ctx['file_info'] = None
        return render_template('status.html', **ctx)

    @app.route('/status/<file_id>')
    def check_status(file_id):
        return jsonify(get_status(file_id))

    @app.route('/download/<file_id>')
    def download_file(file_id):
        status = get_status(file_id)
        out_path = status.get('output_path', '')
        if not out_path or not os.path.exists(out_path):
            return jsonify({'error': 'File not found'}), 404
        title = status.get('video_title', 'download')
        ext = os.path.splitext(out_path)[1]
        filename = f"{title}{ext}"
        return send_file(out_path, as_attachment=True, download_name=filename)

    @app.route('/search', methods=['GET', 'POST'])
    def search_page():
        query = ''
        results = None
        show_thumbnails = request.args.get('show_thumbnails', '0') == '1'
        if request.method == 'POST':
            query = request.form.get('query', '').strip()
        else:
            query = request.args.get('query', '').strip()
        if query:
            results = search_youtube(query)
        ctx = common_ctx()
        ctx.update({'query': query, 'results': results, 'show_thumbnails': show_thumbnails})
        return render_template('search.html', **ctx)

    @app.route('/history')
    def history():
        all_status = get_status()
        history_items = []
        now = time.time()
        for fid, info in all_status.items():
            item = dict(info)
            item['file_id'] = fid
            item['title'] = info.get('video_title', info.get('url', 'Unknown'))
            item['file_exists'] = os.path.exists(info.get('output_path', ''))
            size = info.get('file_size', 0)
            item['file_size_mb'] = round(size / (1024 * 1024), 1) if size else 0
            completed_at = info.get('completed_at', 0)
            if completed_at:
                from datetime import timedelta
                remaining = timedelta(seconds=max(0, completed_at + 6 * 3600 - now))
                item['time_remaining'] = remaining
            else:
                item['time_remaining'] = None
            history_items.append(item)
        history_items.sort(key=lambda x: x.get('completed_at', 0) or x.get('started_at', 0), reverse=True)
        ctx = common_ctx()
        ctx['history_items'] = history_items
        return render_template('history.html', **ctx)

    @app.route('/ping')
    def ping():
        return 'ok'

    return app


def run_server():
    _copy_templates()
    app = _make_app()
    logger.info("Starting Flask server on port 5000...")
    app.run(host='127.0.0.1', port=5000, threaded=True, use_reloader=False)


def start():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    logger.info("Flask server thread started")
    return True
