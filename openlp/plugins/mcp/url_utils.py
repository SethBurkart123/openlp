# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008 OpenLP Developers                                   #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
The :mod:`~openlp.plugins.mcp.url_utils` module contains utilities for handling
both local file paths and URL downloads for the MCP plugin.

This module provides intelligent URL handling with multiple detection methods:

1. **Content-Type Detection**: Makes HTTP HEAD requests to get actual MIME types
2. **URL Pattern Analysis**: Analyzes URLs for common patterns and domains
3. **Extension Mapping**: Comprehensive mapping of MIME types to file extensions
4. **Fallback Handling**: Multiple layers of fallback for reliable file type detection

The module handles URLs from various sources including:
- Image hosting services (Unsplash, Pixabay, Pexels)
- Video platforms (YouTube, Vimeo) 
- Audio services (SoundCloud, Spotify)
- CDNs and APIs without traditional file extensions
- OpenLP service files and presentations

All downloads are cached in temporary directories and automatically cleaned up.
"""

import logging
import tempfile
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

from openlp.core.common.httputils import download_file, get_url_file_size

log = logging.getLogger(__name__)


class DownloadProgress:
    """Simple progress tracker for downloads."""
    def __init__(self):
        self.is_cancelled = False
        
    def update_progress(self, block_count, block_size):
        """Update progress - currently just a no-op for simplicity."""
        pass


def is_url(path_or_url: str) -> bool:
    """
    Check if a string is a URL.
    
    :param path_or_url: The string to check
    :return: True if it's a URL, False if it's a local path
    """
    try:
        parsed = urlparse(path_or_url)
        return parsed.scheme in ('http', 'https', 'ftp', 'ftps')
    except Exception:
        return False


def is_video_platform_url(url: str) -> bool:
    """
    Check if URL is from a video platform that needs special handling with yt-dlp.
    
    :param url: The URL to check
    :return: True if it's from a video platform like YouTube, Vimeo, etc.
    """
    url_lower = url.lower()
    video_platforms = [
        'youtube.com', 'youtu.be', 'youtube-nocookie.com',
        'vimeo.com', 'dailymotion.com', 'twitch.tv',
        'facebook.com/watch', 'instagram.com/p/', 'instagram.com/reel/',
        'tiktok.com', 'twitter.com', 'x.com'
    ]
    return any(platform in url_lower for platform in video_platforms)


def get_content_type_from_url(url: str) -> str:
    """
    Get the content type of a URL by making a HEAD request.
    
    :param url: The URL to check
    :return: The content type, or None if unavailable
    """
    if not HAS_REQUESTS:
        log.debug("Requests module not available, cannot get content type")
        return None
        
    try:
        from openlp.core.common.httputils import get_proxy_settings, get_random_user_agent
        
        # Use OpenLP's proxy settings and user agent
        proxy = get_proxy_settings()
        headers = {'User-Agent': get_random_user_agent()}
        
        response = requests.head(url, headers=headers, proxies=proxy, timeout=10.0, allow_redirects=True)
        return response.headers.get('content-type', '').lower()
    except Exception as e:
        log.debug(f"Could not get content type for {url}: {e}")
        return None


def get_extension_from_content_type(content_type: str) -> str:
    """
    Map content type to file extension.
    
    :param content_type: The MIME content type
    :return: Appropriate file extension including the dot
    """
    if not content_type:
        return '.tmp'
    
    # Handle content types with charset and other parameters
    content_type = content_type.split(';')[0].strip()
    
    # Map of content types to extensions
    content_type_map = {
        # Images
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/bmp': '.bmp',
        'image/tiff': '.tiff',
        'image/tif': '.tiff',
        'image/webp': '.webp',
        'image/svg+xml': '.svg',
        
        # Videos
        'video/mp4': '.mp4',
        'video/avi': '.avi',
        'video/quicktime': '.mov',
        'video/x-msvideo': '.avi',
        'video/x-ms-wmv': '.wmv',
        'video/x-flv': '.flv',
        'video/webm': '.webm',
        'video/3gpp': '.3gp',
        'video/x-matroska': '.mkv',
        
        # Audio
        'audio/mpeg': '.mp3',
        'audio/mp3': '.mp3',
        'audio/wav': '.wav',
        'audio/wave': '.wav',
        'audio/x-wav': '.wav',
        'audio/ogg': '.ogg',
        'audio/flac': '.flac',
        'audio/aac': '.aac',
        'audio/mp4': '.m4a',
        'audio/x-ms-wma': '.wma',
        
        # Documents/Presentations
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.ms-powerpoint.presentation.macroEnabled.12': '.pptm',
        'application/vnd.oasis.opendocument.presentation': '.odp',
        
        # Services
        'application/xml': '.osz',  # OpenLP service files are often XML
        'text/xml': '.osz',
        'application/zip': '.osz',  # Could be OpenLP service
    }
    
    return content_type_map.get(content_type, '.tmp')


def guess_extension_from_url_patterns(url: str) -> str:
    """
    Fallback method to guess file extension from URL patterns.
    This is used when Content-Type detection fails.
    
    :param url: The URL to analyze
    :return: Best guess extension
    """
    url_lower = url.lower()
    
    # Look for common patterns in URLs
    if any(pattern in url_lower for pattern in ['image', 'photo', 'pic', 'img']):
        return '.jpg'  # Most common image format
    elif any(pattern in url_lower for pattern in ['video', 'vid', 'movie']):
        return '.mp4'  # Most common video format
    elif any(pattern in url_lower for pattern in ['audio', 'sound', 'music']):
        return '.mp3'  # Most common audio format
    elif any(pattern in url_lower for pattern in ['presentation', 'slide', 'ppt']):
        return '.pdf'  # Safe format for presentations
    elif any(pattern in url_lower for pattern in ['service', 'osz']):
        return '.osz'  # OpenLP service
    else:
        # Try to guess from domain
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if 'unsplash' in domain or 'pixabay' in domain or 'pexels' in domain:
            return '.jpg'  # Image hosting services
        elif 'youtube' in domain or 'vimeo' in domain:
            return '.mp4'  # Video services (though these would need special handling)
        elif 'soundcloud' in domain or 'spotify' in domain:
            return '.mp3'  # Audio services
        
    return '.tmp'  # Ultimate fallback


def get_filename_from_url(url: str) -> str:
    """
    Extract a filename from a URL, using both URL path and Content-Type detection.
    
    :param url: The URL to extract filename from
    :return: The filename with appropriate extension
    """
    try:
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        
        # If we found a filename with extension in the URL, use it
        if filename and '.' in filename:
            return filename
        
        # Otherwise, try to get content type and generate appropriate filename
        content_type = get_content_type_from_url(url)
        extension = get_extension_from_content_type(content_type)
        
        # If content type detection failed, try URL pattern guessing
        if extension == '.tmp':
            extension = guess_extension_from_url_patterns(url)
        
        # Generate a base filename
        if filename:
            # Use the filename from URL but add proper extension
            base_name = filename
        else:
            # Generate a name based on the URL and detected type
            if extension == '.jpg' or extension.startswith('.') and extension[1:] in ['png', 'gif', 'bmp', 'webp', 'svg']:
                base_name = f"image_{hash(url) % 10000}"
            elif extension.startswith('.') and extension[1:] in ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm']:
                base_name = f"video_{hash(url) % 10000}"
            elif extension.startswith('.') and extension[1:] in ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma']:
                base_name = f"audio_{hash(url) % 10000}"
            elif extension in ['.pptx', '.ppt', '.pdf']:
                base_name = f"presentation_{hash(url) % 10000}"
            elif extension == '.osz':
                base_name = f"service_{hash(url) % 10000}"
            else:
                base_name = f"download_{hash(url) % 10000}"
        
        return base_name + extension
        
    except Exception as e:
        log.debug(f"Error generating filename for {url}: {e}")
        return f"download_{hash(url) % 10000}.tmp"


def download_video_platform_file(url: str, download_path: Path, quality: str = 'bestvideo[height<=1080][vcodec^=avc]+bestaudio/bestvideo[height<=1080]+bestaudio/best') -> bool:
    """
    Download video from platforms like YouTube using yt-dlp.
    
    :param url: The video platform URL
    :param download_path: The path where to save the file (without extension)
    :param quality: The quality format string for yt-dlp (includes video+audio combination)
    :return: True if successful, False otherwise
    """
    if not HAS_YT_DLP:
        log.error("yt-dlp not available for video platform downloads")
        return False
    
    try:
        # Configure yt-dlp options based on user settings
        ydl_opts = {
            'outtmpl': str(download_path.parent / f"{download_path.stem}.%(ext)s"),
            'format': quality,  # Quality string now includes both video and audio preferences
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to get the final filename
            info = ydl.extract_info(url, download=False)
            if not info:
                log.error(f"Could not extract video info from {url}")
                return False
            
            # Download the video
            ydl.download([url])
            
            # Find the downloaded file (yt-dlp adds the extension)
            final_extension = info.get('ext', 'mp4')
            final_path = download_path.parent / f"{download_path.stem}.{final_extension}"
            
            if final_path.exists():
                log.info(f"Successfully downloaded video from {url} to {final_path}")
                return True
            else:
                log.error(f"Downloaded file not found at expected location: {final_path}")
                return False
                
    except Exception as e:
        log.error(f"Failed to download video from {url}: {e}")
        return False


def resolve_file_path(file_path_or_url: str, temp_dir: Path = None, quality: str = 'bestvideo[height<=1080][vcodec^=avc]+bestaudio/bestvideo[height<=1080]+bestaudio/best') -> Path:
    """
    Resolve a file path or URL to a local file path.
    If it's a URL, download it to a temporary location.
    If it's a local path, return it as-is.
    
    :param file_path_or_url: Either a local file path or a URL
    :param temp_dir: Optional temporary directory to download to
    :param quality: Quality setting for video downloads (includes video+audio preferences)
    :return: Path to the local file
    :raises: Exception if download fails or file doesn't exist
    """
    if not file_path_or_url:
        raise ValueError("file_path_or_url cannot be empty")
    
    # Check if it's a URL
    if is_url(file_path_or_url):
        log.info(f"Downloading file from URL: {file_path_or_url}")
        
        # Determine download location
        if temp_dir is None:
            temp_dir = Path(tempfile.gettempdir()) / 'openlp_mcp_downloads'
        
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if this is a video platform URL that needs special handling
        if is_video_platform_url(file_path_or_url):
            log.info(f"Detected video platform URL, using yt-dlp: {file_path_or_url}")
            
            # Generate base filename for video platforms
            base_filename = f"video_{hash(file_path_or_url) % 10000}"
            download_path_base = temp_dir / base_filename
            
            try:
                success = download_video_platform_file(file_path_or_url, download_path_base, quality)
                if not success:
                    raise Exception(f"Failed to download video from {file_path_or_url}")
                
                # Find the actual downloaded file (yt-dlp adds extension)
                for ext in ['mp4', 'webm', 'mkv', 'avi', 'mov']:
                    potential_path = temp_dir / f"{base_filename}.{ext}"
                    if potential_path.exists():
                        log.info(f"Successfully downloaded video to {potential_path}")
                        return potential_path
                
                raise Exception(f"Downloaded video file not found in expected location")
                
            except Exception as e:
                log.error(f"Error downloading video from {file_path_or_url}: {e}")
                # Clean up any partial downloads
                for ext in ['mp4', 'webm', 'mkv', 'avi', 'mov', 'part']:
                    cleanup_path = temp_dir / f"{base_filename}.{ext}"
                    if cleanup_path.exists():
                        try:
                            cleanup_path.unlink()
                        except Exception:
                            pass
                raise Exception(f"Failed to download video from {file_path_or_url}: {e}")
        
        else:
            # Regular file download for non-video platforms
            # Generate filename using improved detection
            filename = get_filename_from_url(file_path_or_url)
            download_path = temp_dir / filename
            
            # Download the file
            progress = DownloadProgress()
            try:
                success = download_file(progress, file_path_or_url, download_path)
                if not success:
                    raise Exception(f"Failed to download file from {file_path_or_url}")
                    
                log.info(f"Successfully downloaded {file_path_or_url} to {download_path}")
                return download_path
                
            except Exception as e:
                log.error(f"Error downloading {file_path_or_url}: {e}")
                # Clean up partial download
                if download_path.exists():
                    try:
                        download_path.unlink()
                    except Exception:
                        pass
                raise Exception(f"Failed to download {file_path_or_url}: {e}")
    
    else:
        # It's a local path
        local_path = Path(file_path_or_url)
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {file_path_or_url}")
        
        return local_path


def clean_temp_downloads(temp_dir: Path = None):
    """
    Clean up temporary downloaded files.
    
    :param temp_dir: Optional specific temp directory to clean
    """
    try:
        if temp_dir is None:
            temp_dir = Path(tempfile.gettempdir()) / 'openlp_mcp_downloads'
        
        if temp_dir.exists() and temp_dir.is_dir():
            for file_path in temp_dir.glob('*'):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                except Exception as e:
                    log.debug(f"Could not clean up {file_path}: {e}")
            
            # Try to remove the directory if it's empty
            try:
                temp_dir.rmdir()
            except Exception:
                pass  # Directory not empty or other error
    
    except Exception as e:
        log.debug(f"Error during temp cleanup: {e}")


def test_url_detection():
    """
    Test function to demonstrate improved URL file type detection.
    This can be called during development to verify detection works correctly.
    """
    test_urls = [
        "https://images.unsplash.com/photo-1469474968028-56623f02e42e?q=80&w=2948&auto=format&fit=crop",
        "https://example.com/video.mp4",
        "https://cdn.example.com/audio",
        "https://api.example.com/presentation.pptx",
        "https://files.example.com/service.osz",
    ]
    
    print("Testing URL detection:")
    for url in test_urls:
        filename = get_filename_from_url(url)
        content_type = get_content_type_from_url(url)
        print(f"URL: {url}")
        print(f"  Detected filename: {filename}")
        print(f"  Content-Type: {content_type or 'Not detected'}")
        print() 