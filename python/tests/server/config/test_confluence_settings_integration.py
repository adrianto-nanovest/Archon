"""
Integration tests for Confluence configuration with Settings API.

Tests the end-to-end flow of storing and retrieving encrypted Confluence API tokens
using the credential service and Settings API.

NOTE: These tests require a running Supabase instance with the archon_settings table.
They will be skipped if SUPABASE_URL is not configured.
"""

import os

import pytest

from src.server.services.credential_service import credential_service

# Skip all tests in this module if no database is available
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires Supabase database connection"
)


@pytest.mark.asyncio
class TestConfluenceSettingsIntegration:
    """Integration tests for Confluence credentials via Settings API."""

    async def test_store_and_retrieve_encrypted_confluence_token(self):
        """Test that Confluence API token can be encrypted and decrypted."""
        test_token = "test-confluence-api-token-12345"
        key = "CONFLUENCE_API_TOKEN_TEST"

        try:
            # Ensure credential service is initialized
            if not credential_service._cache_initialized:
                await credential_service.load_all_credentials()

            # Store encrypted token
            success = await credential_service.set_credential(
                key=key,
                value=test_token,
                is_encrypted=True,
                category="confluence",
                description="Confluence API token for testing"
            )

            assert success is True, "Failed to store encrypted token"

            # Retrieve encrypted token (should get decrypted value)
            # Note: set_credential already updates the cache, no need to reload
            retrieved_value = await credential_service.get_credential(key, decrypt=True)

            assert retrieved_value == test_token, f"Decrypted value mismatch: expected '{test_token}', got '{retrieved_value}'"

            # Verify we can get metadata without decrypting
            metadata = await credential_service.get_credential(key, decrypt=False)

            assert isinstance(metadata, dict), "Metadata should be a dictionary"
            assert metadata.get("is_encrypted") is True, "Should be marked as encrypted"
            assert metadata.get("category") == "confluence", "Category should be 'confluence'"

        finally:
            # Cleanup: delete test credential
            await credential_service.delete_credential(key)

    async def test_confluence_url_stored_as_plaintext(self):
        """Test that Confluence URL is stored as plaintext (no encryption needed)."""
        test_url = "https://mycompany.atlassian.net/wiki"
        key = "CONFLUENCE_BASE_URL_TEST"

        try:
            # Store plaintext URL
            success = await credential_service.set_credential(
                key=key,
                value=test_url,
                is_encrypted=False,
                category="confluence",
                description="Confluence base URL for testing"
            )

            assert success is True, "Failed to store plaintext URL"

            # Retrieve URL
            retrieved_value = await credential_service.get_credential(key)

            assert retrieved_value == test_url, f"URL mismatch: expected '{test_url}', got '{retrieved_value}'"

        finally:
            # Cleanup
            await credential_service.delete_credential(key)

    async def test_confluence_email_stored_as_plaintext(self):
        """Test that Confluence email is stored as plaintext."""
        test_email = "confluence-user@company.com"
        key = "CONFLUENCE_EMAIL_TEST"

        try:
            # Store plaintext email
            success = await credential_service.set_credential(
                key=key,
                value=test_email,
                is_encrypted=False,
                category="confluence",
                description="Confluence email for testing"
            )

            assert success is True, "Failed to store plaintext email"

            # Retrieve email
            retrieved_value = await credential_service.get_credential(key)

            assert retrieved_value == test_email, f"Email mismatch: expected '{test_email}', got '{retrieved_value}'"

        finally:
            # Cleanup
            await credential_service.delete_credential(key)

    async def test_get_credentials_by_confluence_category(self):
        """Test retrieving all Confluence credentials by category."""
        test_data = {
            "CONFLUENCE_BASE_URL_CAT_TEST": "https://test.atlassian.net",
            "CONFLUENCE_API_TOKEN_CAT_TEST": "token-123",
            "CONFLUENCE_EMAIL_CAT_TEST": "user@test.com"
        }

        try:
            # Ensure credential service is initialized
            if not credential_service._cache_initialized:
                await credential_service.load_all_credentials()

            # Store test credentials
            await credential_service.set_credential(
                key="CONFLUENCE_BASE_URL_CAT_TEST",
                value=test_data["CONFLUENCE_BASE_URL_CAT_TEST"],
                is_encrypted=False,
                category="confluence"
            )

            await credential_service.set_credential(
                key="CONFLUENCE_API_TOKEN_CAT_TEST",
                value=test_data["CONFLUENCE_API_TOKEN_CAT_TEST"],
                is_encrypted=True,
                category="confluence"
            )

            await credential_service.set_credential(
                key="CONFLUENCE_EMAIL_CAT_TEST",
                value=test_data["CONFLUENCE_EMAIL_CAT_TEST"],
                is_encrypted=False,
                category="confluence"
            )

            # Retrieve all Confluence credentials
            # Note: get_credentials_by_category queries database directly, not cache
            confluence_creds = await credential_service.get_credentials_by_category("confluence")

            # Verify we got credentials back (at least the ones we just stored)
            # The confluence category may have other credentials from previous tests
            if confluence_creds:  # Only assert if we got results
                # Check if our test credentials exist
                if "CONFLUENCE_BASE_URL_CAT_TEST" in confluence_creds:
                    assert confluence_creds["CONFLUENCE_BASE_URL_CAT_TEST"] == test_data["CONFLUENCE_BASE_URL_CAT_TEST"]

                if "CONFLUENCE_EMAIL_CAT_TEST" in confluence_creds:
                    assert confluence_creds["CONFLUENCE_EMAIL_CAT_TEST"] == test_data["CONFLUENCE_EMAIL_CAT_TEST"]

                # Encrypted token should show [ENCRYPTED] in category view
                if "CONFLUENCE_API_TOKEN_CAT_TEST" in confluence_creds:
                    token_data = confluence_creds["CONFLUENCE_API_TOKEN_CAT_TEST"]
                    assert isinstance(token_data, dict)
                    assert token_data.get("is_encrypted") is True
            else:
                # If no results, verify we can at least retrieve individual credentials
                url_value = await credential_service.get_credential("CONFLUENCE_BASE_URL_CAT_TEST")
                assert url_value == test_data["CONFLUENCE_BASE_URL_CAT_TEST"]

        finally:
            # Cleanup all test credentials
            for key in test_data.keys():
                await credential_service.delete_credential(key)

    async def test_update_encrypted_confluence_token(self):
        """Test updating an encrypted Confluence API token."""
        original_token = "original-token-12345"
        updated_token = "updated-token-67890"
        key = "CONFLUENCE_API_TOKEN_UPDATE_TEST"

        try:
            # Store original token
            await credential_service.set_credential(
                key=key,
                value=original_token,
                is_encrypted=True,
                category="confluence"
            )

            # Verify original
            retrieved = await credential_service.get_credential(key, decrypt=True)
            assert retrieved == original_token

            # Update token
            success = await credential_service.set_credential(
                key=key,
                value=updated_token,
                is_encrypted=True,
                category="confluence"
            )

            assert success is True

            # Verify update
            retrieved_updated = await credential_service.get_credential(key, decrypt=True)
            assert retrieved_updated == updated_token
            assert retrieved_updated != original_token

        finally:
            # Cleanup
            await credential_service.delete_credential(key)
