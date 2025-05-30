"""
Helper module to work around YouTube restrictions on cloud platforms like Railway
"""
import random
import yt_dlp

# List of realistic user agents to rotate through - expanded with latest versions
USER_AGENTS = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    # Firefox on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    # Edge on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.47',
    # Safari on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    # Chrome on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    # Firefox on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
    # Mobile browsers (iPhone, Android)
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36'
]

# Extended list of player client types to try with more options
PLAYER_CLIENTS = ['android', 'web', 'tv_embedded', 'ios', 'tv_html5', 'tv_cast', 'web_embedded', 'web_remix']

# Extended cookie domains to try and simulate a logged-in session
COOKIE_DOMAINS = ['youtube.com', 'google.com', 'accounts.google.com']

# Additional HTTP headers to simulate a real browser
ADDITIONAL_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'DNT': '1',
    'Sec-CH-UA': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
    'Sec-CH-UA-Mobile': '?0',
    'Sec-CH-UA-Platform': '"Windows"',
    'Priority': 'u=0, i'
}

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
    
    # Set up HTTP headers to simulate a real browser
    http_headers = ADDITIONAL_HEADERS.copy()
    http_headers['User-Agent'] = user_agent
    http_headers['Referer'] = random.choice([
        'https://www.youtube.com/',
        'https://www.google.com/search?q=youtube',
        'https://m.youtube.com/',
        'https://www.youtube.com/feed/trending'
    ])
    
    # Create enhanced options
    enhanced_opts = {
        # Use a random, realistic user agent and browser headers
        'user_agent': user_agent,
        'http_headers': http_headers,
        
        # Add multiple extraction attempts with different settings
        'extractor_args': {
            'youtube': {
                'player_client': [player_client],
                'compat_opt': ['no-youtube-unavailable-videos'],
                'player_skip': ['configs', 'webpage'],  # Try to skip additional checks
                'max_comments': ['0'],  # Don't fetch comments - reduces bot signals
                'channel_tab': ['videos']  # Avoid homepage recommendations
            }
        },
        
        # Networking and retry settings
        'socket_timeout': 30,  # Increased timeout
        'retries': 10,  # More retries
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,  # Allow continuing even if some fragments fail
        'retry_sleep_functions': {
            'fragment': lambda n: random.uniform(5, 10) * (n + 1),  # Randomized retry backoff
            'extractor': lambda n: random.uniform(2, 5) * (n + 1),
        },
        
        # Avoid throttling
        'throttled_rate': '100K',
        
        # Advanced networking
        'source_address': '0.0.0.0',  # Use multiple IPs if available
        'geo_bypass': True,  # Try to bypass geo-restrictions
        'geo_bypass_country': 'US',  # Simulate US IP
        
        # Advanced options
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'sleep_interval': random.randint(3, 7),  # Random sleep between requests
        'max_sleep_interval': 10,
        'external_downloader_args': ['-timeout', '30'],  # Timeout for external downloaders
        
        # Cookie handling
        'cookiefile': None,  # Will try to use default cookies
        'cookiesfrombrowser': ['chrome'],  # Try to load cookies from browser
        
        # YouTube-specific
        'youtube_include_dash_manifest': False,  # Skip DASH manifest
        'prefer_insecure': True,  # Prefer HTTP over HTTPS to reduce TLS fingerprinting
        'allow_unplayable_formats': True  # Try to access restricted formats
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
        'no_warnings': False,  # Show warnings for debugging
        'verbose': True,  # More verbose for cloud debugging
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
    
    # Multiple extraction strategies to try
    extraction_strategies = [
        # Strategy 1: Use mobile client
        {'player_client': ['android'], 'user_agent': next(ua for ua in USER_AGENTS if 'Android' in ua)},
        # Strategy 2: Use iOS client
        {'player_client': ['ios'], 'user_agent': next(ua for ua in USER_AGENTS if 'iPhone' in ua)},
        # Strategy 3: Use TV client
        {'player_client': ['tv_embedded'], 'prefer_insecure': True},
        # Strategy 4: Use web with Tor-like behavior
        {'player_client': ['web'], 'user_agent': random.choice(USER_AGENTS), 
         'geo_bypass_country': random.choice(['US', 'GB', 'CA', 'AU'])},
        # Strategy 5: Last resort - try with minimal options
        {'player_client': ['web_remix'], 'youtube_include_dash_manifest': True}
    ]
    
    # Add any YouTube short URL handling
    if 'youtube.com/shorts/' in video_url:
        # Convert shorts URL to normal video URL
        video_id = video_url.split('/')[-1].split('?')[0]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    last_exception = None
    
    # Try each strategy until one works
    for strategy_index, strategy in enumerate(extraction_strategies):
        # Apply enhanced options with this strategy
        final_opts = get_enhanced_ydl_opts(info_opts.copy(), format_type)
        
        # Apply strategy-specific options
        for key, value in strategy.items():
            if key == 'player_client':
                final_opts['extractor_args']['youtube']['player_client'] = value
            else:
                final_opts[key] = value
        
        # Multiple attempts with this strategy
        for attempt in range(3):
            try:
                print(f"Strategy {strategy_index+1}, Attempt {attempt+1}: Extracting info for {video_url}")
                with yt_dlp.YoutubeDL(final_opts) as ydl:
                    info = ydl.extract_info(video_url, download=not skip_download)
                    if info:
                        print(f"Success with strategy {strategy_index+1}!")
                        return info
            except Exception as e:
                last_exception = e
                print(f"Error with strategy {strategy_index+1}, attempt {attempt+1}: {str(e)}")
                
                # Slight delay between attempts to avoid rate limiting
                import time
                time.sleep(random.uniform(1, 3))
                
                # Modify settings slightly for next attempt
                final_opts['user_agent'] = random.choice(USER_AGENTS)
                if 'http_headers' in final_opts:
                    final_opts['http_headers']['User-Agent'] = final_opts['user_agent']
    
    # If all strategies failed, try one more desperate attempt with a completely different approach
    try:
        print("Final attempt with minimal options...")
        minimal_opts = {
            'format': 'worst',  # Try to get any format
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'noplaylist': True,
            'skip_download': skip_download,
            'youtube_include_dash_manifest': False,
            'extractor_args': {'youtube': {'player_client': ['web']}}
        }
        with yt_dlp.YoutubeDL(minimal_opts) as ydl:
            return ydl.extract_info(video_url, download=not skip_download)
    except Exception as e:
        # Re-raise the last exception
        if last_exception:
            print(f"All extraction strategies failed. Last error: {str(last_exception)}")
            raise last_exception
        raise e
    
    return None
