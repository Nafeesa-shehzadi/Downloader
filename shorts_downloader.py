import yt_dlp
import os
import sys

def download_youtube_short(url, output_folder="downloads"):
    """
    Download a YouTube Short video directly
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'best',  # Get the best quality
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': False,  # Show progress
        'no_warnings': False
    }
    
    # Download the video
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading: {url}")
            ydl.download([url])
            print(f"Download completed! Saved to {output_folder}")
    except Exception as e:
        print(f"Error downloading: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    # If URL is provided as command line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
        download_youtube_short(url)
    else:
        # Otherwise ask for URL
        url = input("Enter YouTube Shorts URL: ")
        download_youtube_short(url)
