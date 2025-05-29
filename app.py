import os
import uuid
import subprocess
import traceback
import yt_dlp
from flask import Flask, render_template, request, jsonify, send_from_directory

# Import our YouTube helper module with enhanced anti-bot protection
import youtube_helper

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
        
        try:
            # Use our enhanced YouTube helper to get video info with anti-bot protection
            print(f"Getting info for {video_url} with enhanced protection")
            video_info = youtube_helper.extract_video_info(
                video_url, 
                format_type=format_type,
                quality=quality,
                skip_download=True
            )
        except Exception as e:
            print(f"Error with enhanced protection: {str(e)}")
            return jsonify({"error": f"YouTube is blocking this request. Please try again later or with a different video."}), 500
        
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
        # Create temporary file path
        temp_file = os.path.join(DOWNLOAD_FOLDER, f"temp_{uuid.uuid4()}.{'.mp3' if format_type == 'audio' else '.mp4'}")
        
        try:
            # Use enhanced YouTube helper to download with anti-bot protection
            print(f"Downloading {video_url} with enhanced protection")
            
            # Basic download options
            base_opts = {
                'outtmpl': temp_file,
                'quiet': False,  # Let's see output for debugging
            }
            
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
                    print(f"Download attempt {attempt+1} with options: {enhanced_opts}")
                    info = ydl.extract_info(video_url, download=True)
                    
                    # Check if download succeeded
                    if info and 'requested_downloads' in info and info['requested_downloads']:
                        downloaded_file = info['requested_downloads'][0].get('_filename', temp_file)
                        if os.path.exists(downloaded_file):
                            print(f"Successfully downloaded on attempt {attempt+1}")
                            break
                    else:
                        print(f"Download info not available in attempt {attempt+1}")
            except Exception as e:
                print(f"Error in download attempt {attempt+1}: {str(e)}")
                # Try with different settings on next attempt
                enhanced_opts = youtube_helper.get_enhanced_ydl_opts(base_opts, format_type)
        
        # Check if any of the attempts succeeded
        if not downloaded_file or not os.path.exists(downloaded_file):
            return "Download failed after multiple attempts. YouTube may be blocking access.", 500
                
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
