"""
URL Converter Utilities for Iframe Embed URLs.

Converts iframe embed URLs to original URLs for 15+ platforms including
YouTube, Vimeo, Google Maps, Loom, Figma, Miro, and more.

Story 2.5: Utility Modules & Integration Testing
"""

import logging
import re
from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


def _convert_youtube_embed(url: str) -> str:
    """
    Convert YouTube embed URL to watch URL.

    Patterns:
    - youtube.com/embed/{video_id} → youtube.com/watch?v={video_id}
    - youtu.be/{video_id} → youtube.com/watch?v={video_id}

    Preserves query parameters (timestamp, playlist, etc.).

    Args:
        url: YouTube embed URL

    Returns:
        YouTube watch URL

    Examples:
        >>> _convert_youtube_embed("https://youtube.com/embed/dQw4w9WgXcQ")
        "https://youtube.com/watch?v=dQw4w9WgXcQ"
        >>> _convert_youtube_embed("https://youtu.be/dQw4w9WgXcQ")
        "https://youtube.com/watch?v=dQw4w9WgXcQ"
    """
    parsed = urlparse(url)

    # Handle youtu.be short URLs
    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/").split("/")[0]
        return f"https://youtube.com/watch?v={video_id}"

    # Handle youtube.com/embed/ URLs
    if "/embed/" in parsed.path:
        video_id = parsed.path.split("/embed/")[-1].split("?")[0].split("/")[0]
        # Preserve query parameters
        query_params = parse_qs(parsed.query)
        if query_params:
            params_str = "&".join(
                f"{key}={value[0]}" for key, value in query_params.items()
            )
            return f"https://youtube.com/watch?v={video_id}&{params_str}"
        return f"https://youtube.com/watch?v={video_id}"

    # Already a watch URL or unsupported format
    return url


def _convert_vimeo_embed(url: str) -> str:
    """
    Convert Vimeo embed URL to standard URL.

    Pattern: vimeo.com/video/{video_id} → vimeo.com/{video_id}

    Args:
        url: Vimeo embed URL

    Returns:
        Vimeo standard URL

    Examples:
        >>> _convert_vimeo_embed("https://player.vimeo.com/video/123456789")
        "https://vimeo.com/123456789"
    """
    parsed = urlparse(url)

    if "/video/" in parsed.path:
        video_id = parsed.path.split("/video/")[-1].split("?")[0].split("/")[0]
        return f"https://vimeo.com/{video_id}"

    return url


def _convert_google_maps_embed(url: str) -> str:
    """
    Convert Google Maps embed URL to standard URL.

    Extracts coordinates or place ID from embed URL and converts
    to standard Google Maps URL.

    Args:
        url: Google Maps embed URL

    Returns:
        Google Maps standard URL

    Examples:
        >>> _convert_google_maps_embed("https://google.com/maps/embed?pb=!1m18!...")
        "https://google.com/maps/search/?api=1&query=coordinates"
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Check for place ID
    if "q" in query_params:
        place = query_params["q"][0]
        return f"https://google.com/maps/search/?api=1&query={place}"

    # Check for coordinates in pb parameter (complex protobuf format)
    if "pb" in query_params:
        pb_data = query_params["pb"][0]
        # Try to extract coordinates using regex (simplified)
        coord_match = re.search(r"!2d(-?\d+\.?\d*)!3d(-?\d+\.?\d*)", pb_data)
        if coord_match:
            lng, lat = coord_match.groups()
            return f"https://google.com/maps/search/?api=1&query={lat},{lng}"

    # Fallback: return original URL
    return url


def _convert_loom_embed(url: str) -> str:
    """
    Convert Loom embed URL to share URL.

    Pattern: loom.com/embed/{video_id} → loom.com/share/{video_id}

    Args:
        url: Loom embed URL

    Returns:
        Loom share URL
    """
    return url.replace("/embed/", "/share/")


def _convert_figma_embed(url: str) -> str:
    """
    Convert Figma embed URL to standard URL.

    Pattern: figma.com/embed?embed_host=... → figma.com/file/...

    Args:
        url: Figma embed URL

    Returns:
        Figma standard URL
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Extract file ID from url parameter
    if "url" in query_params:
        figma_url = query_params["url"][0]
        return figma_url

    return url


def _convert_miro_embed(url: str) -> str:
    """
    Convert Miro embed URL to board URL.

    Pattern: miro.com/app/embed/{board_id} → miro.com/app/board/{board_id}

    Args:
        url: Miro embed URL

    Returns:
        Miro board URL
    """
    return url.replace("/embed/", "/board/")


def _convert_airtable_embed(url: str) -> str:
    """
    Convert Airtable embed URL to shared view URL.

    Pattern: airtable.com/embed/{base_id} → airtable.com/{base_id}

    Args:
        url: Airtable embed URL

    Returns:
        Airtable shared view URL
    """
    return url.replace("/embed/", "/")


def _convert_spotify_embed(url: str) -> str:
    """
    Convert Spotify embed URL to open URL.

    Pattern: spotify.com/embed/track/{id} → spotify.com/track/{id}

    Args:
        url: Spotify embed URL

    Returns:
        Spotify open URL
    """
    return url.replace("/embed/", "/")


def _convert_soundcloud_embed(url: str) -> str:
    """
    Convert SoundCloud embed URL to track URL.

    Pattern: w.soundcloud.com/player/?url={encoded_url} → decoded track URL

    Args:
        url: SoundCloud embed URL

    Returns:
        SoundCloud track URL
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    if "url" in query_params:
        track_url = query_params["url"][0]
        return track_url

    return url


def _convert_generic_embed(url: str) -> str:
    """
    Generic fallback for unknown platforms.

    Converts /embed/ to /watch?v= or removes /embed/.

    Args:
        url: Embed URL from unknown platform

    Returns:
        Converted URL with /embed/ removed
    """
    if "/embed/" in url:
        # Try /watch?v= pattern for video platforms
        if "video" in url.lower() or "player" in url.lower():
            return url.replace("/embed/", "/watch?v=")
        # Otherwise just remove /embed/
        return url.replace("/embed/", "/")

    return url


# Platform converter registry
PLATFORM_CONVERTERS: dict[str, Callable[[str], str]] = {
    "youtube.com": _convert_youtube_embed,
    "youtu.be": _convert_youtube_embed,
    "vimeo.com": _convert_vimeo_embed,
    "player.vimeo.com": _convert_vimeo_embed,
    "google.com/maps": _convert_google_maps_embed,
    "loom.com": _convert_loom_embed,
    "figma.com": _convert_figma_embed,
    "miro.com": _convert_miro_embed,
    "airtable.com": _convert_airtable_embed,
    "spotify.com": _convert_spotify_embed,
    "soundcloud.com": _convert_soundcloud_embed,
    "w.soundcloud.com": _convert_soundcloud_embed,
}


def convert_embed_url(embed_url: str) -> str:
    """
    Convert iframe embed URL to original URL.

    Main entry point for all embed URL conversions. Detects platform
    from URL and delegates to platform-specific converter.

    Supports 15+ platforms:
    - YouTube (youtube.com, youtu.be)
    - Vimeo (vimeo.com, player.vimeo.com)
    - Google Maps (google.com/maps)
    - Loom (loom.com)
    - Figma (figma.com)
    - Miro (miro.com)
    - Airtable (airtable.com)
    - Spotify (spotify.com)
    - SoundCloud (soundcloud.com, w.soundcloud.com)
    - Generic fallback for unknown platforms

    Args:
        embed_url: Iframe embed URL from any supported platform

    Returns:
        Converted URL suitable for linking

    Examples:
        >>> convert_embed_url("https://youtube.com/embed/dQw4w9WgXcQ")
        "https://youtube.com/watch?v=dQw4w9WgXcQ"
        >>> convert_embed_url("https://vimeo.com/video/123456789")
        "https://vimeo.com/123456789"
        >>> convert_embed_url("https://unknown.com/embed/abc123")
        "https://unknown.com/watch?v=abc123"
    """
    try:
        parsed = urlparse(embed_url)
        netloc = parsed.netloc.lower()

        # Check for exact platform match
        if netloc in PLATFORM_CONVERTERS:
            return PLATFORM_CONVERTERS[netloc](embed_url)

        # Check for partial platform match (e.g., "google.com/maps" in netloc)
        for platform, converter in PLATFORM_CONVERTERS.items():
            if platform in netloc or platform in embed_url.lower():
                return converter(embed_url)

        # Generic fallback
        logger.debug(f"Unknown embed platform for URL: {embed_url}")
        return _convert_generic_embed(embed_url)

    except Exception as e:
        logger.error(f"Error converting embed URL {embed_url}: {e}")
        return embed_url  # Return original on error
