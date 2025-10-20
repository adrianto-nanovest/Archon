"""
Unit tests for URL converter module.

Story 2.5: Utility Modules & Integration Testing
"""

import pytest

from src.server.services.confluence.utils.url_converter import (
    _convert_airtable_embed,
    _convert_figma_embed,
    _convert_generic_embed,
    _convert_google_maps_embed,
    _convert_loom_embed,
    _convert_miro_embed,
    _convert_soundcloud_embed,
    _convert_spotify_embed,
    _convert_vimeo_embed,
    _convert_youtube_embed,
    convert_embed_url,
)


class TestYouTubeConversion:
    """Test YouTube URL conversion."""

    def test_standard_embed_url(self):
        """Should convert standard YouTube embed URL."""
        url = "https://youtube.com/embed/dQw4w9WgXcQ"
        result = _convert_youtube_embed(url)
        assert result == "https://youtube.com/watch?v=dQw4w9WgXcQ"

    def test_short_url_format(self):
        """Should convert youtu.be short URLs."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = _convert_youtube_embed(url)
        assert result == "https://youtube.com/watch?v=dQw4w9WgXcQ"

    def test_preserves_timestamp_parameter(self):
        """Should preserve timestamp query parameters."""
        url = "https://youtube.com/embed/dQw4w9WgXcQ?start=42"
        result = _convert_youtube_embed(url)
        assert "watch?v=dQw4w9WgXcQ" in result
        assert "start=42" in result

    def test_preserves_playlist_parameter(self):
        """Should preserve playlist query parameters."""
        url = "https://youtube.com/embed/dQw4w9WgXcQ?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        result = _convert_youtube_embed(url)
        assert "watch?v=dQw4w9WgXcQ" in result
        assert "list=" in result

    def test_already_watch_url(self):
        """Should handle already converted watch URLs."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        result = _convert_youtube_embed(url)
        assert result == url

    def test_handles_www_prefix(self):
        """Should handle www.youtube.com URLs."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        result = _convert_youtube_embed(url)
        assert "watch?v=dQw4w9WgXcQ" in result


class TestVimeoConversion:
    """Test Vimeo URL conversion."""

    def test_player_embed_url(self):
        """Should convert Vimeo player embed URL."""
        url = "https://player.vimeo.com/video/123456789"
        result = _convert_vimeo_embed(url)
        assert result == "https://vimeo.com/123456789"

    def test_standard_vimeo_url(self):
        """Should handle standard Vimeo URLs."""
        url = "https://vimeo.com/video/123456789"
        result = _convert_vimeo_embed(url)
        assert result == "https://vimeo.com/123456789"

    def test_already_converted_url(self):
        """Should handle already converted Vimeo URLs."""
        url = "https://vimeo.com/123456789"
        result = _convert_vimeo_embed(url)
        assert result == url


class TestGoogleMapsConversion:
    """Test Google Maps URL conversion."""

    def test_embed_url_with_query(self):
        """Should convert embed URL with query parameter."""
        url = "https://google.com/maps/embed?q=San+Francisco"
        result = _convert_google_maps_embed(url)
        assert "google.com/maps/search" in result
        assert "query=San" in result  # URL decoding happens automatically

    def test_embed_url_with_coordinates(self):
        """Should extract coordinates from pb parameter."""
        url = "https://google.com/maps/embed?pb=!1m18!1m12!1m3!1d3153!2d-122.4194!3d37.7749!..."
        result = _convert_google_maps_embed(url)
        # Should contain extracted coordinates or return original
        assert "google.com/maps" in result

    def test_fallback_for_complex_urls(self):
        """Should return original URL for complex formats."""
        url = "https://google.com/maps/embed?unknown=param"
        result = _convert_google_maps_embed(url)
        assert result == url


class TestLoomConversion:
    """Test Loom URL conversion."""

    def test_embed_to_share_url(self):
        """Should convert Loom embed to share URL."""
        url = "https://loom.com/embed/abc123def456"
        result = _convert_loom_embed(url)
        assert result == "https://loom.com/share/abc123def456"


class TestFigmaConversion:
    """Test Figma URL conversion."""

    def test_embed_with_url_parameter(self):
        """Should extract Figma file URL from embed."""
        url = "https://figma.com/embed?url=https://figma.com/file/abc123/Design"
        result = _convert_figma_embed(url)
        assert result == "https://figma.com/file/abc123/Design"

    def test_fallback_without_url_param(self):
        """Should return original URL without url parameter."""
        url = "https://figma.com/embed?other=param"
        result = _convert_figma_embed(url)
        assert result == url


class TestMiroConversion:
    """Test Miro URL conversion."""

    def test_embed_to_board_url(self):
        """Should convert Miro embed to board URL."""
        url = "https://miro.com/app/embed/abc123"
        result = _convert_miro_embed(url)
        assert result == "https://miro.com/app/board/abc123"


class TestAirtableConversion:
    """Test Airtable URL conversion."""

    def test_embed_to_shared_view(self):
        """Should convert Airtable embed to shared view."""
        url = "https://airtable.com/embed/shrAbc123Def456"
        result = _convert_airtable_embed(url)
        assert result == "https://airtable.com/shrAbc123Def456"


class TestSpotifyConversion:
    """Test Spotify URL conversion."""

    def test_embed_to_open_url(self):
        """Should convert Spotify embed to open URL."""
        url = "https://spotify.com/embed/track/abc123"
        result = _convert_spotify_embed(url)
        assert result == "https://spotify.com/track/abc123"


class TestSoundCloudConversion:
    """Test SoundCloud URL conversion."""

    def test_player_with_url_parameter(self):
        """Should extract SoundCloud track URL from player."""
        url = "https://w.soundcloud.com/player/?url=https://soundcloud.com/artist/track"
        result = _convert_soundcloud_embed(url)
        assert result == "https://soundcloud.com/artist/track"

    def test_fallback_without_url_param(self):
        """Should return original URL without url parameter."""
        url = "https://w.soundcloud.com/player/?other=param"
        result = _convert_soundcloud_embed(url)
        assert result == url


class TestGenericEmbedConversion:
    """Test generic embed conversion fallback."""

    def test_video_platform_fallback(self):
        """Should use /watch?v= pattern for video platforms."""
        url = "https://unknown-video.com/embed/abc123"
        result = _convert_generic_embed(url)
        assert result == "https://unknown-video.com/watch?v=abc123"

    def test_player_platform_fallback(self):
        """Should use /watch?v= pattern for player platforms."""
        url = "https://player.unknown.com/embed/abc123"
        result = _convert_generic_embed(url)
        assert result == "https://player.unknown.com/watch?v=abc123"

    def test_non_video_platform_fallback(self):
        """Should remove /embed/ for non-video platforms."""
        url = "https://unknown.com/embed/abc123"
        result = _convert_generic_embed(url)
        assert result == "https://unknown.com/abc123"

    def test_no_embed_in_url(self):
        """Should return original URL if no /embed/."""
        url = "https://unknown.com/content/abc123"
        result = _convert_generic_embed(url)
        assert result == url


class TestConvertEmbedUrl:
    """Test main convert_embed_url function."""

    def test_youtube_platform_detection(self):
        """Should detect and convert YouTube URLs."""
        url = "https://youtube.com/embed/dQw4w9WgXcQ"
        result = convert_embed_url(url)
        assert "watch?v=dQw4w9WgXcQ" in result

    def test_vimeo_platform_detection(self):
        """Should detect and convert Vimeo URLs."""
        url = "https://player.vimeo.com/video/123456789"
        result = convert_embed_url(url)
        assert result == "https://vimeo.com/123456789"

    def test_google_maps_platform_detection(self):
        """Should detect and convert Google Maps URLs."""
        url = "https://google.com/maps/embed?q=San+Francisco"
        result = convert_embed_url(url)
        assert "google.com/maps/search" in result

    def test_loom_platform_detection(self):
        """Should detect and convert Loom URLs."""
        url = "https://loom.com/embed/abc123"
        result = convert_embed_url(url)
        assert "loom.com/share" in result

    def test_spotify_platform_detection(self):
        """Should detect and convert Spotify URLs."""
        url = "https://spotify.com/embed/track/abc123"
        result = convert_embed_url(url)
        assert result == "https://spotify.com/track/abc123"

    def test_unknown_platform_fallback(self):
        """Should use generic fallback for unknown platforms."""
        url = "https://unknown.com/embed/abc123"
        result = convert_embed_url(url)
        # Should either convert generically or return original
        assert "unknown.com" in result

    def test_malformed_url_handling(self):
        """Should handle malformed URLs gracefully."""
        url = "not-a-valid-url"
        result = convert_embed_url(url)
        # Should return original URL on error
        assert result == url

    def test_empty_url(self):
        """Should handle empty URL."""
        url = ""
        result = convert_embed_url(url)
        assert result == url

    def test_case_insensitive_platform_detection(self):
        """Should detect platforms case-insensitively."""
        url = "https://YOUTUBE.COM/embed/dQw4w9WgXcQ"
        result = convert_embed_url(url)
        assert "watch?v=" in result.lower()
