from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import os
import uuid
import re
import traceback
import subprocess

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
        
        # Basic configuration for info extraction
        info_opts = {
            'format': 'best',
            'noplaylist': True,
            'restrictfilenames': True,
            'skip_download': True,  # Just get info first
            'quiet': True
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


@app.route('/stream-download', methods=['GET'])
def stream_download():
    """Stream a YouTube video/audio directly to the browser"""
    video_url = request.args.get('url')
    format_type = request.args.get('format', 'video')
    quality = request.args.get('quality', 'best')
    
    if not video_url:
        return "No URL provided", 400
    
    try:
        # Get video info first
        info_opts = {
            'format': 'best',
            'noplaylist': True,
            'restrictfilenames': True,
        }
        
        # Configure for audio/video and quality
        if format_type == 'audio':
            info_opts.update({'format': 'bestaudio'})
            # Check if FFmpeg is available
            try:
                subprocess_result = subprocess.run(['ffmpeg', '-version'], 
                                                stdout=subprocess.PIPE, 
                                                stderr=subprocess.PIPE, 
                                                shell=True)
                ffmpeg_available = subprocess_result.returncode == 0
            except:
                ffmpeg_available = False
                
            if ffmpeg_available:
                info_opts.update({
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '256',
                    }],
                })
        elif quality != 'best':
            if quality == '1080':
                info_opts.update({'format': 'best[height<=1080]'})
            elif quality == '720':
                info_opts.update({'format': 'best[height<=720]'})
            elif quality == '480':
                info_opts.update({'format': 'best[height<=480]'})
        
        # Create temporary file path
        temp_file = os.path.join(DOWNLOAD_FOLDER, f"temp_{uuid.uuid4()}.{'.mp3' if format_type == 'audio' else '.mp4'}")
        info_opts['outtmpl'] = temp_file
        
        # Download the file
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            
            # Get actual filename (might be different from temp_file due to conversion)
            if 'requested_downloads' in info and info['requested_downloads']:
                downloaded_file = info['requested_downloads'][0].get('_filename', temp_file)
            else:
                downloaded_file = temp_file
                
            if not os.path.exists(downloaded_file):
                return "Download failed", 500
                
            # Generate a safe filename for the browser
            safe_title = ''.join(c for c in info['title'] if c.isalnum() or c in ' -_').strip()
            safe_title = safe_title.replace(' ', '_')
            
            # Add short indicator if it's a YouTube Short
            if 'youtube.com/shorts/' in video_url:
                safe_title = f"Short_{safe_title}"
                
            # Determine content type and file extension
            if format_type == 'audio':
                content_type = 'audio/mpeg'
                filename = f"{safe_title}.mp3"
            else:
                content_type = 'video/mp4'
                filename = f"{safe_title}.mp4"
            
            # Stream the file to the browser
            def generate():
                with open(downloaded_file, 'rb') as f:
                    while True:
                        chunk = f.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        yield chunk
                # Delete the temp file after streaming
                try:
                    os.remove(downloaded_file)
                except:
                    pass
                    
            response = app.response_class(
                generate(),
                mimetype=content_type,
                direct_passthrough=True
            )
            response.headers.set('Content-Disposition', f'attachment; filename="{filename}"')
            return response
                
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error streaming: {error_details}")
        return f"Error: {str(e)}", 500

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
