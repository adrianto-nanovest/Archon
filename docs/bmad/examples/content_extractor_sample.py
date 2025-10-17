"""
Simplified content extractor wrapper.
Integrates with existing enhanced_renderer.py for content processing.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.enhanced_renderer import EnhancedContentRenderer
from src.confluence_client import ConfluenceClient
from src.jira_client import JiraClient

class ContentExtractor:
  """
  Simplified wrapper around the existing enhanced content renderer.
  Maintains compatibility while simplifying the interface.
  """

  def __init__(self, confluence_client: ConfluenceClient, jira_client: Optional[JiraClient] = None):
    """
    Initialize content extractor.

    Args:
        confluence_client: Confluence API client
        jira_client: Optional JIRA API client
    """
    self.confluence_client = confluence_client
    self.jira_client = jira_client
    self.logger = logging.getLogger("ContentExtractor")

    # Initialize the enhanced renderer (existing production code)
    self.enhanced_renderer = EnhancedContentRenderer()

  async def extract_content(self, page_id: str) -> Dict[str, Any]:
    """
    Extract and process page content using enhanced renderer.

    This method now calls get_page_content internally to fetch complete API data,
    then processes the content and extracts comprehensive metadata.

    Args:
        page_id: Confluence page ID

    Returns:
        Dictionary with processed content, metadata, and discovered assets
    """
    try:
      # Get complete page content from Confluence API
      page_data = await self.confluence_client.get_page_content(page_id)

      page_title = page_data['title']
      page_content_html = page_data['content_html']
      space_id = page_data['space_id']

      self.logger.info(f"Extracting content for page {page_id}: {page_title}")

      # Prepend the page title as an H1 heading to the HTML content
      html_with_title = f"<h1>{page_title}</h1><br/><br/>{page_content_html}"

      # This maintains all the complex processing logic that was optimized
      markdown_content = await self.enhanced_renderer.render_content(
        html_content=html_with_title,
        page_id=page_id,
        space_id=space_id,
        confluence_client=self.confluence_client,
        jira_client=self.jira_client
      )

      # Get discovered assets from the renderer
      discovered_assets = self.enhanced_renderer.get_discovered_assets()
      self.logger.info(f"Discovered {len(discovered_assets)} assets in page {page_id}")

      # Get full asset metadata if we have discovered assets
      asset_links_metadata = []
      if discovered_assets:
        try:
          # Get all page attachments from API
          all_assets = await self.confluence_client.get_page_attachments(page_id)

          # Create a lookup dict for API assets by title (filename)
          assets_by_title = {asset.title: asset for asset in all_assets}

          # Build full metadata for discovered assets
          for filename in discovered_assets:
            if filename in assets_by_title:
              asset = assets_by_title[filename]
              asset_links_metadata.append({
                'id': asset.id.value,
                'title': asset.title,
                'type': asset.type,
                'size': asset.size,
                'mimetype': asset.mime_type,
                'download_url': asset.download_url,
                'drive_url': None  # Will be populated after processing
              })
        except Exception as e:
          self.logger.warning(f"Failed to get asset metadata for page {page_id}: {str(e)}")

      # Get additional metadata from enhanced renderer
      external_links = getattr(self.enhanced_renderer, 'external_links', [])
      internal_links = getattr(self.enhanced_renderer, 'internal_links', [])
      jira_issue_links = getattr(self.enhanced_renderer, 'jira_issue_links', [])
      user_mentions = getattr(self.enhanced_renderer, 'user_mentions', [])

      # Build comprehensive metadata for RAG optimization using API data
      metadata = {
        'page_id': page_id,
        'title': page_title,
        'url': page_data['url'],
        'space_key': page_data['space_key'],
        'space_id': page_data['space_id'],
        'version': page_data['version'],
        'parent': page_data['parent'],
        'ancestors': page_data['ancestors'],
        'children': page_data['children'],
        'created_by': page_data['created_by'],
        'created_at': page_data['created_at'],
        'last_updated_at': page_data['last_updated_at'],
        'external_links': external_links,
        'internal_links': internal_links,
        'jira_issue_links': jira_issue_links,
        'user_mentions': user_mentions,
        'asset_links': asset_links_metadata,
        'extracted_at': datetime.now().isoformat(),
        'content_length': len(markdown_content),
        'word_count': len(markdown_content.split())
      }

      return {
        'content': markdown_content,
        'metadata': metadata,
        'discovered_assets': discovered_assets
      }

    except Exception as e:
      self.logger.error(f"Failed to extract content for page {page_id}: {str(e)}")

      # Return minimal content on error
      return {
        'content': f"# Page {page_id}\n\n*Content extraction failed: {str(e)}*",
        'metadata': {
          'page_id': page_id,
          'extracted_at': datetime.now().isoformat()
        },
        'error': str(e)
      }
