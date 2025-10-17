"""
CQL Injection Prevention Tests for Confluence Integration

Tests that space key validation prevents CQL injection attacks.

CQL (Confluence Query Language) is similar to SQL and can be vulnerable to injection
attacks if user input is not properly validated before constructing queries.

Test Coverage:
1. SQL injection attempts via malicious space key input
2. Invalid space key formats (lowercase, spaces, special chars)
3. Valid space key acceptance (uppercase alphanumeric)
4. Empty string handling
5. Buffer overflow attempts (extremely long space keys)

Expected Behavior:
All invalid space keys should raise ValueError with a clear message.
Valid space keys should be accepted (DEVDOCS, IT123, PROJ, etc.).
"""

import pytest

from src.server.services.confluence.confluence_validator import validate_space_key


class TestCQLInjectionPrevention:
    """Test suite for CQL injection prevention via space key validation."""

    def test_valid_space_keys(self):
        """Test that legitimate space keys are accepted."""
        valid_keys = [
            "DEVDOCS",
            "IT",
            "PROJ123",
            "DEV",
            "MARKETING2025",
            "A",  # Single letter
            "ABC123XYZ",
        ]

        for space_key in valid_keys:
            assert validate_space_key(space_key) is True, f"{space_key} should be valid"

    def test_sql_injection_attempt(self):
        """Test that SQL injection attempts via space key are rejected."""
        malicious_inputs = [
            "SPACE'; DROP TABLE confluence_pages--",
            "SPACE' OR '1'='1",
            "SPACE'; DELETE FROM pages--",
            "SPACE' UNION SELECT * FROM users--",
            "'; DROP TABLE--",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError) as exc_info:
                validate_space_key(malicious_input)

            assert "Invalid space key format" in str(exc_info.value)
            assert malicious_input in str(exc_info.value)

    def test_invalid_lowercase(self):
        """Test that lowercase space keys are rejected."""
        invalid_keys = [
            "devdocs",
            "lowercase",
            "Dev",  # Mixed case
            "dEVDOCS",  # Mixed case
        ]

        for space_key in invalid_keys:
            with pytest.raises(ValueError) as exc_info:
                validate_space_key(space_key)

            assert "Invalid space key format" in str(exc_info.value)
            assert "uppercase" in str(exc_info.value).lower()

    def test_invalid_with_spaces(self):
        """Test that space keys with spaces are rejected."""
        invalid_keys = [
            "SPACE KEY",
            "DEV DOCS",
            "IT 123",
            " DEVDOCS",  # Leading space
            "DEVDOCS ",  # Trailing space
            "DEV  DOCS",  # Double space
        ]

        for space_key in invalid_keys:
            with pytest.raises(ValueError) as exc_info:
                validate_space_key(space_key)

            assert "Invalid space key format" in str(exc_info.value)

    def test_invalid_special_characters(self):
        """Test that space keys with special characters are rejected."""
        invalid_keys = [
            "DEV-DOCS",
            "DEV_DOCS",
            "DEV.DOCS",
            "DEV@DOCS",
            "DEV#123",
            "DEV$MONEY",
            "DEV!",
            "DEV%",
            "DEV&CO",
            "DEV()",
            "DEV+PLUS",
            "DEV=EQUAL",
        ]

        for space_key in invalid_keys:
            with pytest.raises(ValueError) as exc_info:
                validate_space_key(space_key)

            assert "Invalid space key format" in str(exc_info.value)
            assert "alphanumeric" in str(exc_info.value).lower()

    def test_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(ValueError) as exc_info:
            validate_space_key("")

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_starts_with_number(self):
        """Test that space keys starting with a number are rejected."""
        invalid_keys = [
            "123DEV",
            "1",
            "99PROBLEMS",
        ]

        for space_key in invalid_keys:
            with pytest.raises(ValueError) as exc_info:
                validate_space_key(space_key)

            assert "Invalid space key format" in str(exc_info.value)
            assert "starting with a letter" in str(exc_info.value).lower()

    def test_extremely_long_space_key(self):
        """Test that extremely long space keys are rejected (buffer overflow protection)."""
        # Create a valid but very long space key
        long_key = "A" + "B" * 300  # 301 characters

        with pytest.raises(ValueError) as exc_info:
            validate_space_key(long_key)

        assert "too long" in str(exc_info.value).lower()
        assert "255" in str(exc_info.value)

    def test_null_and_non_string_types(self):
        """Test that null and non-string types are rejected."""
        invalid_inputs = [
            None,
            123,
            12.34,
            [],
            {},
            True,
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises((ValueError, TypeError)):
                validate_space_key(invalid_input)  # type: ignore

    def test_unicode_and_non_ascii(self):
        """Test that Unicode and non-ASCII characters are rejected."""
        invalid_keys = [
            "DËVDÖCS",  # Accented chars
            "DEVДOCS",  # Cyrillic
            "DEV文档",  # Chinese
            "DEV🚀",  # Emoji
        ]

        for space_key in invalid_keys:
            with pytest.raises(ValueError) as exc_info:
                validate_space_key(space_key)

            assert "Invalid space key format" in str(exc_info.value)

    def test_cql_injection_via_boolean_logic(self):
        """Test that boolean logic injection attempts are rejected."""
        malicious_inputs = [
            "SPACE OR 1=1",
            "SPACE AND 1=1",
            "SPACE' OR '1'='1",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError) as exc_info:
                validate_space_key(malicious_input)

            assert "Invalid space key format" in str(exc_info.value)

    def test_error_message_quality(self):
        """Test that error messages are clear and helpful."""
        try:
            validate_space_key("invalid-key")
        except ValueError as e:
            error_msg = str(e)

            # Error should mention the invalid input
            assert "invalid-key" in error_msg

            # Error should provide guidance
            assert "uppercase" in error_msg.lower() or "alphanumeric" in error_msg.lower()

            # Error should provide examples
            assert "DEVDOCS" in error_msg or "IT123" in error_msg

    def test_edge_case_single_character(self):
        """Test single character space keys (valid edge case)."""
        valid_single_chars = ["A", "B", "Z"]

        for space_key in valid_single_chars:
            assert validate_space_key(space_key) is True

    def test_edge_case_max_length(self):
        """Test space key at maximum allowed length (255 chars)."""
        # Create a valid 255-character space key
        max_length_key = "A" + "B" * 254

        assert len(max_length_key) == 255
        assert validate_space_key(max_length_key) is True
