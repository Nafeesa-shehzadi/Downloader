from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import os
import uuid
import re
import traceback
import subprocess

app = Flask(__name__)

# Configuration
# Use a folder in the user's Downloads folder
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "YouTubeDownloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# For debugging
print(f"Downloads will be saved to: {DOWNLOAD_FOLDER}")

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
        # Basic configuration that works reliably
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'restrictfilenames': True,  # Avoid special characters in filenames
        }
        
        # Handle audio downloads
        if format_type == 'audio':
            print("Audio format selected")
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
                ydl_opts.update({
                    'format': 'bestaudio',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '256',
                    }],
                })
            else:
                ydl_opts.update({
                    'format': 'bestaudio',
                })
        # Handle video quality for video downloads
        elif format_type == 'video' and quality != 'best':
            if quality == '1080':
                ydl_opts.update({'format': 'best[height<=1080]'})
            elif quality == '720':
                ydl_opts.update({'format': 'best[height<=720]'})
            elif quality == '480':
                ydl_opts.update({'format': 'best[height<=480]'})
        
        # Print debugging info
        print(f"Downloading {video_url} to {DOWNLOAD_FOLDER}")
        print(f"Options: {ydl_opts}")
        
        # Perform the download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            
            # Get the filename that was actually downloaded
            if info and 'requested_downloads' in info and info['requested_downloads']:
                download_info = info['requested_downloads'][0]
                filename = download_info.get('_filename')
                
                if filename and os.path.exists(filename):
                    print(f"Successfully downloaded: {filename}")
                    
                    # Determine download type for the message
                    if 'youtube.com/shorts/' in video_url:
                        download_type = "YouTube Short"
                    else:
                        download_type = "YouTube Video"
                        
                    if format_type == 'audio':
                        download_type += " audio"
                        
                    return jsonify({
                        "success": True,
                        "message": f"Download completed! The {download_type} has been saved to your Downloads folder.",
                        "filename": os.path.basename(filename)
                    })
                else:
                    print("Download appears to have failed - no file found")
                    return jsonify({"error": "Download failed - no file was created"}), 500
            else:
                print("No download info available")
                return jsonify({"error": "No download information available"}), 500
                
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error: {error_details}")
        return jsonify({"error": str(e)}), 500

# We don't need this route anymore since files are saved directly to Downloads folder
# @app.route('/downloads/<path:filename>', methods=['GET'])
# def download_file(filename):
#     return "Files are saved directly to your Downloads folder"

# We don't need this route anymore since the user can access their Downloads folder directly
# @app.route('/open-folder')
# def open_folder():
#     return "No longer needed"

if __name__ == '__main__':
    app.run(debug=True)
