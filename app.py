          flash('Failed to split file. Please try with fewer parts or check the logs.')
                return redirect(url_for('split_tool'))
        except Exception as e:
            logger.error(f"Error splitting file: {str(e)}")
            flash('An error occurred while splitting the file.')
            return redirect(url_for('split_tool'))

    # GET request - show available files
    files = []
    for filename in os.listdir(DOWNLOAD_FOLDER):
        # Only show main files, not split parts
        if filename.endswith('.3gp') or filename.endswith('.mp3'):
            if '_part' not in filename:  # Skip already split parts
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                file_id = os.path.splitext(filename)[0]

                # Get file info
                info = get_file_info(file_path)

                files.append({
                    'filename': filename,
                    'file_id': file_id,
                    'size': os.path.getsize(file_path),
                    'size_human': info['size_human'],
                    'size_mb': info['size_mb'],
                    'format': info['format'],
                    'duration_human': info['duration_human'],
                    'duration_seconds': info['duration_seconds']
                })

    # Sort by newest first (based on filename which contains timestamp hash)
    files.sort(key=lambda x: x['filename'], reverse=True)

    return render_template('split_tool.html', files=files)

@app.route('/search', methods=['GET', 'POST'])
def search():
    # Check if showing thumbnails (default: no, to save data on 2G)
    show_thumbnails = request.args.get('show_thumbnails', '0') == '1'

    # Get query from POST (new search) or GET (thumbnail toggle)
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
    else:
        query = request.args.get('query', '').strip()

    # If no query, show the search form
    if not query:
        if request.method == 'POST':
            flash('Please enter a search term')
        return render_template('search.html', results=None, query='', show_thumbnails=show_thumbnails)

    # Execute the search (query is guaranteed to exist here)
    try:
        # Use yt-dlp to search YouTube (no API key required)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'socket_timeout': 300,  # Timeout for 2G networks
        }

        # Add cookies if available (helps with rate limiting and bot detection)
        if has_cookies():
            ydl_opts['cookiefile'] = COOKIES_FILE

        results = []
        search_results = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for up to 10 results with timeout protection
                search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"Search DownloadError: {error_msg}")
            if 'timeout' in error_msg.lower():
                flash('Search timed out. Please check your connection and try again.')
            elif '429' in error_msg or 'too many requests' in error_msg.lower():
                flash('Too many search requests. Please wait a few minutes and try again.')
            elif '403' in error_msg or 'forbidden' in error_msg.lower():
                flash('YouTube blocked the search. Try uploading cookies from /cookies page.')
            else:
                flash('YouTube search error. Please try again.')
            return render_template('search.html', results=None, query=query, show_thumbnails=show_thumbnails)
        except Exception as e:
            logger.error(f"Search extraction error: {str(e)}")
            flash('Search failed. Please try again later.')
            return render_template('search.html', results=None, query=query, show_thumbnails=show_thumbnails)

        # Process search results
        if search_results and 'entries' in search_results:
            for entry in search_results['entries']:
                if entry and entry.get('id'):  # Ensure entry has an ID
                    duration = entry.get('duration', 0)
                    duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "Unknown"

                    # Format upload date
                    upload_date = entry.get('upload_date', '')
                    upload_date_str = "Unknown"
                    if upload_date and len(upload_date) == 8:  # Format: YYYYMMDD
                        try:
                            upload_date_str = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[0:4]}"
                        except:
                            upload_date_str = "Unknown"

                    # Format view count
                    view_count = entry.get('view_count', 0)
                    if view_count:
                        if view_count >= 1000000:
                            view_str = f"{view_count/1000000:.1f}M views"
                        elif view_count >= 1000:
                            view_str = f"{view_count/1000:.1f}K views"
                        else:
                            view_str = f"{view_count} views"
                    else:
                        view_str = "Unknown views"

                    # FIXED: Proper URL construction for YouTube videos
                    # yt-dlp flat extraction may return partial URLs or video IDs
                    video_id = entry.get('id', '')
                    video_url = entry.get('url', '')

                    # Construct proper YouTube URL
                    if video_url and video_url.startswith('http'):
                        # Already a full URL
                        final_url = video_url
                    elif video_id:
                        # Construct from video ID
                        final_url = f"https://www.youtube.com/watch?v={video_id}"
                    else:
                        # Fallback: try to extract from URL field
                        logger.warning(f"Could not determine URL for search result: {entry.get('title', 'Unknown')}")
                        continue  # Skip this result

                    # Get thumbnail URL (small thumbnail for 2G networks)
                    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/default.jpg"

                    results.append({
                        'title': entry.get('title', 'Unknown'),
                        'url': final_url,
                        'duration': duration_str,
                        'duration_seconds': duration,
                        'upload_date': upload_date_str,
                        'channel': entry.get('channel', entry.get('uploader', 'Unknown')),
                        'views': view_str,
                        'thumbnail': thumbnail_url,
                    })

        # Validate we got results
        if not results:
            flash('No results found. Try different search terms.')
            return render_template('search.html', results=[], query=query, show_thumbnails=show_thumbnails)

        return render_template('search.html', results=results, query=query, show_thumbnails=show_thumbnails)

    except Exception as e:
        # Catch any unexpected errors not handled by inner try-except
        logger.error(f"Unexpected search error: {str(e)}")
        flash('An unexpected error occurred. Please try again.')
        return render_template('search.html', results=None, query=query, show_thumbnails=show_thumbnails)

@app.route('/cookies', methods=['GET', 'POST'])
def cookies_page():
    if request.method == 'POST':
        if 'cookies_file' in request.files:
            file = request.files['cookies_file']
            if file.filename == '':
                flash('No file selected')
                return redirect(url_for('cookies_page'))

            if file and file.filename and file.filename.endswith('.txt'):
                try:
                    content = file.read().decode('utf-8')

                    if 'youtube.com' not in content.lower():
                        flash('Invalid cookie file: must contain YouTube cookies')
                        return redirect(url_for('cookies_page'))

                    with open(COOKIES_FILE, 'w') as f:
                        f.write(content)

                    is_valid, validation_msg = validate_cookies()
                    if not is_valid:
                        os.remove(COOKIES_FILE)
                        flash(f'Cookie validation failed: {validation_msg}')
                        return redirect(url_for('cookies_page'))

                    flash('Cookies uploaded and validated successfully!')
                    return redirect(url_for('cookies_page'))
                except Exception as e:
                    flash(f'Error uploading cookies: {str(e)}')
                    return redirect(url_for('cookies_page'))
            else:
                flash('Please upload a .txt file')
                return redirect(url_for('cookies_page'))

        elif 'delete_cookies' in request.form:
            try:
                if os.path.exists(COOKIES_FILE):
                    os.remove(COOKIES_FILE)
                flash('Cookies deleted successfully')
            except Exception as e:
                flash(f'Error deleting cookies: {str(e)}')
            return redirect(url_for('cookies_page'))

    cookies_exist = has_cookies()
    is_valid, message = validate_cookies() if cookies_exist else (False, "No cookies uploaded")

    return render_template('cookies.html', 
                         cookies_exist=cookies_exist, 
                         is_valid=is_valid, 
                         validation_message=message)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
