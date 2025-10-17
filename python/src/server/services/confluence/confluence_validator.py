"""Confluence data validation utilities.

This module provides input validation functions for Confluence integration
to prevent security vulnerabilities like CQL injection attacks.

Validation functions raise ValueError with clear messages on invalid input.
"""

import re


def validate_space_key(space_key: str) -> bool:
    """Validate Confluence space key format.

    Space keys must be uppercase alphanumeric, starting with a letter.
    This prevents CQL injection attacks by ensuring only safe characters.

    Args:
        space_key: The space key to validate

    Returns:
        True if valid

    Raises:
        ValueError: If space key format is invalid

    Examples:
        Valid: DEVDOCS, IT, PROJ123
        Invalid: dev-docs (lowercase), SPACE KEY (space), '; DROP TABLE--' (SQL injection)
    """
    if not space_key:
        raise ValueError("Space key cannot be empty")

    if not isinstance(space_key, str):
        raise ValueError(f"Space key must be a string, got {type(space_key).__name__}")

    # Space keys must be uppercase alphanumeric, starting with a letter
    if not re.match(r"^[A-Z][A-Z0-9]*$", space_key):
        raise ValueError(
            f"Invalid space key format: '{space_key}'. "
            "Space keys must be uppercase alphanumeric, starting with a letter (e.g., DEVDOCS, IT123)."
        )

    # Reasonable length limit (Confluence space keys are typically 2-255 chars)
    if len(space_key) > 255:
        raise ValueError(f"Space key too long: {len(space_key)} characters (max 255)")

    return True
