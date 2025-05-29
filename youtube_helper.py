"""
Helper module to work around YouTube restrictions on cloud platforms like Railway
"""
import random
import yt_dlp

# List of realistic user agents to rotate through
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0'
]

# Extended list of player client types to try
PLAYER_CLIENTS = ['android', 'web', 'tv_embedded']

def get_enhanced_ydl_opts(base_opts=None, format_type='video'):
    """
    Get enhanced yt-dlp options to help bypass YouTube restrictions
    
    Args:
        base_opts (dict): Base options to extend
        format_type (str): 'video' or 'audio'
        
    Returns:
        dict: Enhanced options for yt-dlp
    """
    if base_opts is None:
        base_opts = {}
    
    # Select a random user agent
    user_agent = random.choice(USER_AGENTS)
    
    # Select a random player client
    player_client = random.choice(PLAYER_CLIENTS)
    
    # Create enhanced options
    enhanced_opts = {
        # Use a random, realistic user agent
        'user_agent': user_agent,
        'referer': 'https://www.youtube.com/',
        
        # Add multiple extraction attempts with different settings
        'extractor_args': {
            'youtube': {
                'player_client': [player_client],
                'compat_opt': ['no-youtube-unavailable-videos'],
            }
        },
        
        # Networking and retry settings
        'socket_timeout': 20,
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': False,
        'retry_sleep_functions': {'fragment': lambda n: 5 * (n + 1)},
        
        # Avoid throttling
        'throttled_rate': '100K',
        
        # Use multiple IPs if available (Railway might have multiple outbound IPs)
        'source_address': '0.0.0.0',
        
        # More aggressive settings
        'nocheckcertificate': True,
        'ignoreerrors': True
    }
    
    # Merge with base options
    for key, value in enhanced_opts.items():
        if key not in base_opts:
            base_opts[key] = value
        elif key == 'extractor_args' and 'extractor_args' in base_opts:
            # Merge extractor args
            for extractor, args in enhanced_opts['extractor_args'].items():
                if extractor in base_opts['extractor_args']:
                    for arg_name, arg_value in args.items():
                        base_opts['extractor_args'][extractor][arg_name] = arg_value
                else:
                    base_opts['extractor_args'][extractor] = args
    
    return base_opts

def extract_video_info(video_url, format_type='video', quality='best', skip_download=True):
    """
    Extract video information with enhanced anti-bot protection
    
    Args:
        video_url (str): YouTube URL
        format_type (str): 'video' or 'audio'
        quality (str): Quality setting ('best', '1080', '720', '480')
        skip_download (bool): Whether to skip the actual download
        
    Returns:
        dict: Video information
    """
    # Start with basic options
    info_opts = {
        'format': 'best',
        'noplaylist': True,
        'restrictfilenames': True,
        'quiet': True,
        'skip_download': skip_download,
    }
    
    # Format specific settings
    if format_type == 'audio':
        info_opts.update({'format': 'bestaudio'})
    elif quality != 'best':
        if quality == '1080':
            info_opts.update({'format': 'best[height<=1080]'})
        elif quality == '720':
            info_opts.update({'format': 'best[height<=720]'})
        elif quality == '480':
            info_opts.update({'format': 'best[height<=480]'})
    
    # Apply enhanced options
    final_opts = get_enhanced_ydl_opts(info_opts, format_type)
    
    # Try to extract info with multiple approaches if needed
    for attempt in range(3):
        try:
            with yt_dlp.YoutubeDL(final_opts) as ydl:
                return ydl.extract_info(video_url, download=not skip_download)
        except Exception as e:
            if attempt < 2:
                # Change settings and try again
                final_opts['extractor_args']['youtube']['player_client'] = [random.choice(PLAYER_CLIENTS)]
                final_opts['user_agent'] = random.choice(USER_AGENTS)
                continue
            raise e
    
    return None
