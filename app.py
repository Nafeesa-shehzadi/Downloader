import os
import uuid
import subprocess
import traceback
import yt_dlp
import time
import socket
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, stream_with_context, Response
from werkzeug.serving import is_running_from_reloader
from threading import Thread

# Import our YouTube helper module with enhanced anti-bot protection
import youtube_helper

# Set socket timeout globally to prevent hanging connections
socket.setdefaulttimeout(30)

app = Flask(__name__)

# Configuration
# For deployments to platforms like Replit, we'll use a temporary folder
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# For debugging
print(f"Temporary download folder: {DOWNLOAD_FOLDER}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')
    format_type = data.get('format', 'video')  # Default to video if not specified
    quality = data.get('quality', 'best')  # Default to best quality if not specified
    
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        # Get video info first to determine filename and other details
        video_info = None
        file_extension = 'mp4'  # Default extension
        
        # Log the request details for debugging
        print(f"Processing request - URL: {video_url}, Format: {format_type}, Quality: {quality}")
        print(f"Request headers: {dict(request.headers)}")
        
        try:
            # Use our enhanced YouTube helper to get video info with anti-bot protection
            print(f"Getting info for {video_url} with enhanced protection")
            video_info = youtube_helper.extract_video_info(
                video_url, 
                format_type=format_type,
                quality=quality,
                skip_download=True
            )
            
            # Log success for debugging
            if video_info:
                print(f"Successfully retrieved info for video: {video_info.get('title', 'Unknown')}")
        except Exception as e:
            error_message = str(e)
            print(f"Error with enhanced protection: {error_message}")
            
            # Provide more specific error messages based on the error
            if "sign in to confirm you're not a bot" in error_message.lower() or "confirm your identity" in error_message.lower():
                return jsonify({"error": "YouTube's anti-bot protection is blocking this request. We're actively working on a solution."}), 429
            elif "unavailable" in error_message.lower() or "private" in error_message.lower():
                return jsonify({"error": "This video is unavailable or private."}), 404
            elif "copyright" in error_message.lower():
                return jsonify({"error": "This video is blocked due to copyright restrictions."}), 403
            else:
                return jsonify({"error": f"YouTube is blocking this request. Please try again later or with a different video."}), 500
        
        # Define basic info options
        info_opts = {
            'format': 'best',
            'noplaylist': True,
            'restrictfilenames': True,
            'quiet': True,
            'skip_download': True
        }
        
        # Special format configuration for audio
        if format_type == 'audio':
            info_opts.update({'format': 'bestaudio'})
            file_extension = 'mp3'
        # Handle video quality for video downloads
        elif quality != 'best':
            if quality == '1080':
                info_opts.update({'format': 'best[height<=1080]'})
            elif quality == '720':
                info_opts.update({'format': 'best[height<=720]'})
            elif quality == '480':
                info_opts.update({'format': 'best[height<=480]'})
        
        # Get video info
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            video_info = ydl.extract_info(video_url, download=False)
        
        if not video_info:
            return jsonify({"error": "Could not retrieve video information"}), 500
        
        # Generate a safe filename
        safe_title = ''.join(c for c in video_info['title'] if c.isalnum() or c in ' -_').strip()
        safe_title = safe_title.replace(' ', '_')
        
        # Determine content type and file extension based on format
        content_type = 'video/mp4'
        if format_type == 'audio':
            content_type = 'audio/mpeg'
            download_type = "Audio"
        else:
            download_type = "Video"
            
        # Add short indicator if it's a YouTube Short
        is_short = 'youtube.com/shorts/' in video_url
        filename_prefix = 'Short_' if is_short else ''
        
        # Create a download URL that will be streamed directly to browser
        download_url = f"/stream-download?url={video_url}&format={format_type}&quality={quality}"
        
        # Return success with the streaming URL
        return jsonify({
            "success": True,
            "message": f"Ready to download! Click the button below to get your {download_type}.",
            "download_url": download_url,
            "filename": f"{filename_prefix}{safe_title}.{file_extension}"
        })
                
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error: {error_details}")
        return jsonify({"error": str(e)}), 500


# Background download queue for handling Railway timeouts
download_queue = {}

@app.route('/initiate-download', methods=['GET'])
def initiate_download():
    """Initiate an asynchronous download process and return a job ID"""
    video_url = request.args.get('url')
    format_type = request.args.get('format', 'video')
    quality = request.args.get('quality', 'best')
    
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400
    
    # Generate a job ID
    job_id = str(uuid.uuid4())
    
    # Set up the job in the queue
    download_queue[job_id] = {
        'status': 'pending',
        'progress': 0,
        'file_path': None,
        'error': None,
        'info': None,
        'started_at': time.time()
    }
    
    # Start background download thread
    download_thread = Thread(target=background_download, 
                            args=(job_id, video_url, format_type, quality))
    download_thread.daemon = True
    download_thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'pending',
        'message': 'Download initiated. Check status with /download-status endpoint.'
    })

@app.route('/download-status/<job_id>', methods=['GET'])
def download_status(job_id):
    """Check the status of a download job"""
    if job_id not in download_queue:
        return jsonify({'error': 'Invalid job ID'}), 404
    
    job = download_queue[job_id]
    
    # Check for timeout (10 minutes)
    if job['status'] == 'pending' and (time.time() - job['started_at']) > 600:
        job['status'] = 'failed'
        job['error'] = 'Download timed out after 10 minutes'
    
    response = {
        'status': job['status'],
        'progress': job['progress']
    }
    
    if job['status'] == 'completed':
        # Add download info
        response['download_url'] = f"/download-file/{job_id}"
        if job['info'] and 'title' in job['info']:
            response['title'] = job['info']['title']
            # Create safe filename
            safe_title = ''.join(c for c in job['info']['title'] if c.isalnum() or c in ' -_').strip()
            safe_title = safe_title.replace(' ', '_')
            response['filename'] = f"{safe_title}.{'mp3' if format_type == 'audio' else 'mp4'}"
    elif job['status'] == 'failed':
        response['error'] = job['error']
    
    return jsonify(response)

@app.route('/download-file/<job_id>', methods=['GET'])
def download_file(job_id):
    """Download the processed file"""
    if job_id not in download_queue:
        return "Invalid job ID", 404
    
    job = download_queue[job_id]
    
    if job['status'] != 'completed' or not job['file_path'] or not os.path.exists(job['file_path']):
        return "File not ready or no longer available", 404
    
    # Determine content type based on file extension
    content_type = 'audio/mpeg' if job['file_path'].endswith('.mp3') else 'video/mp4'
    
    # Create safe filename
    filename = "download.mp4"
    if job['info'] and 'title' in job['info']:
        safe_title = ''.join(c for c in job['info']['title'] if c.isalnum() or c in ' -_').strip()
        safe_title = safe_title.replace(' ', '_')
        filename = f"{safe_title}.{'mp3' if job['file_path'].endswith('.mp3') else 'mp4'}"
    
    # Stream the file to avoid timeout issues
    return send_from_directory(
        os.path.dirname(job['file_path']),
        os.path.basename(job['file_path']),
        mimetype=content_type,
        as_attachment=True,
        download_name=filename
    )

def background_download(job_id, video_url, format_type, quality):
    """Background thread for downloading YouTube content"""
    job = download_queue[job_id]
    
    try:
        # Create temporary file path
        temp_file = os.path.join(DOWNLOAD_FOLDER, f"temp_{job_id}.{'.mp3' if format_type == 'audio' else '.mp4'}")
        
        # Basic download options
        base_opts = {
            'outtmpl': temp_file,
            'quiet': False,  # Output for debugging
            'progress_hooks': [lambda d: update_progress(job_id, d)],
        }
        
        print(f"[Job {job_id}] Downloading {video_url} with enhanced protection")
        
        # Add audio post-processing if needed
        if format_type == 'audio':
            # Check if FFmpeg is available
            try:
                subprocess_result = subprocess.run(['ffmpeg', '-version'], 
                                                stdout=subprocess.PIPE, 
                                                stderr=subprocess.PIPE, 
                                                shell=True)
                ffmpeg_available = subprocess_result.returncode == 0
                
                if ffmpeg_available:
                    base_opts.update({
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '256',
                        }],
                    })
            except:
                pass
        
        # Get download format based on quality selection
        if quality != 'best' and format_type == 'video':
            if quality == '1080':
                base_opts.update({'format': 'best[height<=1080]'})
            elif quality == '720':
                base_opts.update({'format': 'best[height<=720]'})
            elif quality == '480':
                base_opts.update({'format': 'best[height<=480]'})
        
        # Enhance options with anti-bot protection
        enhanced_opts = youtube_helper.get_enhanced_ydl_opts(base_opts, format_type)
        
        # Download the file with multiple attempts if needed
        downloaded_file = None
        info = None
        
        for attempt in range(3):
            try:
                with yt_dlp.YoutubeDL(enhanced_opts) as ydl:
                    # Verbose output for debugging
                    print(f"[Job {job_id}] Download attempt {attempt+1}")
                    info = ydl.extract_info(video_url, download=True)
                    
                    # Check if download succeeded
                    if info and 'requested_downloads' in info and info['requested_downloads']:
                        downloaded_file = info['requested_downloads'][0].get('_filename', temp_file)
                        if os.path.exists(downloaded_file):
                            print(f"[Job {job_id}] Successfully downloaded on attempt {attempt+1}")
                            break
                    else:
                        print(f"[Job {job_id}] Download info not available in attempt {attempt+1}")
            except Exception as e:
                print(f"[Job {job_id}] Error in download attempt {attempt+1}: {str(e)}")
                # Try with different settings on next attempt
                enhanced_opts = youtube_helper.get_enhanced_ydl_opts(base_opts, format_type)
        
        # Check if any of the attempts succeeded
        if not downloaded_file or not os.path.exists(downloaded_file):
            job['status'] = 'failed'
            job['error'] = 'Download failed after multiple attempts. YouTube may be blocking access.'
            return
        
        # Mark job as completed
        job['status'] = 'completed'
        job['file_path'] = downloaded_file
        job['info'] = info
        job['progress'] = 100
        print(f"[Job {job_id}] Download complete: {downloaded_file}")
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[Job {job_id}] Error: {error_details}")
        job['status'] = 'failed'
        job['error'] = str(e)

def update_progress(job_id, progress_data):
    """Update the progress of a download job"""
    if job_id in download_queue:
        job = download_queue[job_id]
        
        if progress_data.get('status') == 'downloading':
            # Calculate progress percentage
            downloaded = progress_data.get('downloaded_bytes', 0)
            total = progress_data.get('total_bytes') or progress_data.get('total_bytes_estimate', 0)
            
            if total > 0:
                progress = int((downloaded / total) * 100)
                job['progress'] = min(progress, 99)  # Cap at 99% until fully complete

@app.route('/stream-download', methods=['GET'])
def stream_download():
    """Legacy endpoint - now redirects to the new asynchronous download system"""
    video_url = request.args.get('url')
    format_type = request.args.get('format', 'video')
    quality = request.args.get('quality', 'best')
    
    if not video_url:
        return "No URL provided", 400
    
    # Redirect to the new async download flow
    return jsonify({
        "error": "This endpoint is deprecated. Please use the new download flow.",
        "redirect": f"/initiate-download?url={video_url}&format={format_type}&quality={quality}"
    }), 302

# We don't need this route anymore since files are saved directly to Downloads folder
# @app.route('/downloads/<path:filename>', methods=['GET'])
# def download_file(filename):
#     return "Files are saved directly to your Downloads folder"

# We don't need this route anymore since the user can access their Downloads folder directly
# @app.route('/open-folder')
# def open_folder():
#     return "No longer needed"

if __name__ == '__main__':
    # Use environment variables for host and port if available (for Railway)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    # When running locally, use debug mode
    debug = host == '127.0.0.1'
    
    app.run(host=host, port=port, debug=debug)
