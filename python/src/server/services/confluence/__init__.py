"""Confluence Cloud API integration services.

This module provides the ConfluenceClient wrapper for interacting with
Confluence Cloud REST API v2 using the atlassian-python-api SDK.
"""

from .confluence_client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceNotFoundError,
    ConfluenceRateLimitError,
)

__all__ = [
    "ConfluenceClient",
    "ConfluenceAuthError",
    "ConfluenceRateLimitError",
    "ConfluenceNotFoundError",
]
