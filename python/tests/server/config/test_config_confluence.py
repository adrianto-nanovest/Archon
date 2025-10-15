"""
Unit tests for Confluence configuration validation.

Tests the validation logic for Confluence environment variables including:
- URL format validation (HTTPS requirement)
- Atlassian Cloud and custom domain support
- Optional configuration handling
- Environment variable loading
"""

import os
from unittest.mock import patch

import pytest

from src.server.config.config import (
    ConfigurationError,
    EnvironmentConfig,
    load_environment_config,
    validate_confluence_url,
)


class TestConfluenceUrlValidation:
    """Test suite for validate_confluence_url function."""

    def test_valid_atlassian_cloud_url(self):
        """Test validation of standard Atlassian Cloud URL."""
        url = "https://company.atlassian.net/wiki"
        assert validate_confluence_url(url) is True

    def test_valid_custom_domain(self):
        """Test validation of custom domain URL."""
        url = "https://wiki.company.com"
        assert validate_confluence_url(url) is True

    def test_valid_atlassian_cloud_without_wiki_path(self):
        """Test validation of Atlassian Cloud URL without /wiki path."""
        url = "https://mycompany.atlassian.net"
        assert validate_confluence_url(url) is True

    def test_invalid_http_url(self):
        """Test that HTTP URLs are rejected (HTTPS required)."""
        url = "http://company.atlassian.net/wiki"
        with pytest.raises(ConfigurationError) as exc_info:
            validate_confluence_url(url)
        assert "must use HTTPS" in str(exc_info.value)

    def test_invalid_empty_url(self):
        """Test that empty URLs are rejected."""
        with pytest.raises(ConfigurationError) as exc_info:
            validate_confluence_url("")
        assert "cannot be empty" in str(exc_info.value)

    def test_invalid_malformed_url(self):
        """Test that malformed URLs are rejected."""
        url = "not-a-valid-url"
        with pytest.raises(ConfigurationError) as exc_info:
            validate_confluence_url(url)
        assert "must use HTTPS" in str(exc_info.value)

    def test_invalid_url_without_scheme(self):
        """Test that URLs without scheme are rejected."""
        url = "company.atlassian.net/wiki"
        with pytest.raises(ConfigurationError) as exc_info:
            validate_confluence_url(url)
        assert "must use HTTPS" in str(exc_info.value)

    def test_invalid_url_without_domain(self):
        """Test that URLs without domain are rejected."""
        url = "https://"
        with pytest.raises(ConfigurationError) as exc_info:
            validate_confluence_url(url)
        assert "must be a valid URL" in str(exc_info.value)


class TestLoadEnvironmentConfig:
    """Test suite for load_environment_config with Confluence variables."""

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "PORT": "8051",
        "CONFLUENCE_BASE_URL": "https://mycompany.atlassian.net/wiki",
        "CONFLUENCE_API_TOKEN": "test-token-123",
        "CONFLUENCE_EMAIL": "test@company.com"
    })
    def test_load_with_all_confluence_variables(self):
        """Test loading config with all Confluence variables set."""
        config = load_environment_config()

        assert isinstance(config, EnvironmentConfig)
        assert config.confluence_base_url == "https://mycompany.atlassian.net/wiki"
        assert config.confluence_api_token == "test-token-123"
        assert config.confluence_email == "test@company.com"

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "PORT": "8051"
    }, clear=True)
    def test_load_without_confluence_variables(self):
        """Test that config loads successfully without Confluence variables."""
        config = load_environment_config()

        assert isinstance(config, EnvironmentConfig)
        assert config.confluence_base_url is None
        assert config.confluence_api_token is None
        assert config.confluence_email is None

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "PORT": "8051",
        "CONFLUENCE_BASE_URL": "https://wiki.custom.com",
        "CONFLUENCE_API_TOKEN": "token-xyz",
        "CONFLUENCE_EMAIL": "user@custom.com"
    })
    def test_load_with_custom_domain(self):
        """Test loading config with custom Confluence domain."""
        config = load_environment_config()

        assert config.confluence_base_url == "https://wiki.custom.com"
        assert config.confluence_api_token == "token-xyz"
        assert config.confluence_email == "user@custom.com"

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "PORT": "8051",
        "CONFLUENCE_BASE_URL": "http://company.atlassian.net/wiki"
    })
    def test_load_with_invalid_confluence_url_fails(self):
        """Test that invalid Confluence URL raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_environment_config()
        assert "must use HTTPS" in str(exc_info.value)

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "PORT": "8051",
        "CONFLUENCE_BASE_URL": "https://mycompany.atlassian.net/wiki"
    })
    def test_url_validation_only_runs_when_url_provided(self):
        """Test that URL validation only runs when confluence_base_url is provided."""
        # This should succeed because URL is valid
        config = load_environment_config()
        assert config.confluence_base_url == "https://mycompany.atlassian.net/wiki"

        # Without URL, no validation should occur (tested in test_load_without_confluence_variables)

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "PORT": "8051",
        "CONFLUENCE_BASE_URL": "https://company.atlassian.net",
        "CONFLUENCE_API_TOKEN": "partial-token"
        # Missing CONFLUENCE_EMAIL - should still work
    })
    def test_partial_confluence_config(self):
        """Test that partial Confluence config is allowed."""
        config = load_environment_config()

        assert config.confluence_base_url == "https://company.atlassian.net"
        assert config.confluence_api_token == "partial-token"
        assert config.confluence_email is None  # Missing but allowed


class TestConfluenceUrlEdgeCases:
    """Test edge cases for Confluence URL validation."""

    def test_url_with_trailing_slash(self):
        """Test URL with trailing slash."""
        url = "https://company.atlassian.net/wiki/"
        assert validate_confluence_url(url) is True

    def test_url_with_port(self):
        """Test custom domain URL with port number."""
        url = "https://wiki.internal.com:8443"
        assert validate_confluence_url(url) is True

    def test_url_with_subdomain(self):
        """Test Atlassian URL with additional subdomains."""
        url = "https://dev.company.atlassian.net/wiki"
        assert validate_confluence_url(url) is True

    def test_non_atlassian_https_url(self):
        """Test that non-Atlassian HTTPS URLs are accepted as custom domains."""
        url = "https://confluence.example.org"
        assert validate_confluence_url(url) is True
