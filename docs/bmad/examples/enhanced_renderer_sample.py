"""
Enhanced Content Renderer for special Confluence elements.

This module provides specialized rendering capabilities for complex Confluence elements
that require special handling beyond standard HTML-to-Markdown conversion.
"""
import logging
import re
from typing import Dict, List
from bs4 import BeautifulSoup, Tag, NavigableString
import markdownify
import os
import json
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path

from src.confluence_client import ConfluenceClient
from src.jira_client import JiraClient


class MacroIdentifier:
  """
  Identifies and classifies Confluence macros in HTML content.

  This class provides methods to identify and extract information about
  various Confluence macros, such as code blocks, panels, status macros, etc.
  """

  def __init__(self):
    """Initialize the MacroIdentifier."""
    self.logger = logging.getLogger("MacroIdentifier")

  def extract_macro_parameters(self, macro: Tag) -> Dict[str, str]:
    """
    Extract parameters from a Confluence macro.

    Args:
        macro: The BeautifulSoup Tag representing the macro.

    Returns:
        A dictionary of parameter names to values.
    """
    parameters = {}

    try:
      # Find all parameter tags
      param_tags = macro.find_all('ac:parameter')

      for param in param_tags:
        param_name = param.get('ac:name', '')
        if param_name:
          parameters[param_name] = param.get_text(strip=True)

      return parameters
    except Exception as e:
      self.logger.error(f"Error extracting macro parameters: {e}")
      return parameters


class MacroParser:
  """
  Parses Confluence macros and converts them to appropriate Markdown or HTML representations.
  """

  def __init__(self, asset_links=None, jira_issue_links=None, external_links=None):
    """Initialize the MacroParser."""
    self.logger = logging.getLogger("MacroParser")
    self.macro_identifier = MacroIdentifier()
    # Fix: Use 'is None' check to preserve empty list references
    self.asset_links = asset_links if asset_links is not None else []
    self.jira_issue_links = jira_issue_links if jira_issue_links is not None else []
    self.external_links = external_links if external_links is not None else []

  def parse_code_macro(self, macro: Tag) -> str:
    """
    Parse a Confluence code macro and convert it to Markdown code block.

    Args:
        macro: The BeautifulSoup Tag representing the code macro.

    Returns:
        A Markdown code block representation.
    """
    try:
      # Extract code content
      content_element = macro.find('ac:plain-text-body')
      if not content_element:
        return "```\nCode block content not found\n```"

      # Preserve leading/trailing whitespace within the body
      code_content = content_element.get_text(strip=False)

      # Ensure code content starts and ends with newlines if it has content,
      # to properly format the code block in Markdown.
      if code_content and not code_content.startswith('\n'):
        code_content = '\n' + code_content
      if code_content and not code_content.endswith('\n'):
        code_content += '\n'
      # If code_content became empty (e.g. only whitespace that was stripped for JSON check)
      elif not code_content:
        code_content = '\n'  # Ensure empty code blocks are still valid

      # Format as Markdown code block
      return f"```{code_content}```"
    except Exception as e:
      self.logger.error(f"Error parsing code macro: {e}")
      return "```\nError parsing code block\n```"

  def parse_panel_macro(self, macro: Tag, panel_type: str = 'panel') -> str:
    """
    Parse a Confluence panel macro (including info, note, warning) and convert it to Markdown.

    Args:
        macro: The BeautifulSoup Tag representing the panel macro.
        panel_type: The type of panel (panel, info, note, warning).

    Returns:
        A Markdown representation of the panel.
    """
    try:
      # Extract panel content
      content_element = macro.find('ac:rich-text-body')
      if not content_element:
        return f"> **{panel_type.upper()}**: Content not found"

      # Convert content to Markdown
      content_html = str(content_element)
      content_md = markdownify.markdownify(content_html, heading_style="ATX")

      # Format based on panel type
      panel_prefix = {
          'panel': '> ',
          'info': '> ℹ️  ',
          'tip': '> ✅  ',
          'note': '> ⚠️  ',
          'warning': '> ❌  ',
      }.get(panel_type, '> ')

      # Format the panel with title if present
      result = []
      # Add content lines with proper prefix
      for line in content_md.split('\n'):
        result.append(f"{panel_prefix} {line}")

      return '\n'.join(result)
    except Exception as e:
      self.logger.error(f"Error parsing {panel_type} macro: {e}")
      return f"> **{panel_type.upper()}**: Error parsing content"

  def parse_status_macro(self, macro: Tag) -> str:
    """
    Parse a Confluence status macro and convert it to Markdown.

    Args:
        macro: The BeautifulSoup Tag representing the status macro.

    Returns:
        A Markdown representation of the status.
    """
    try:
      # Extract parameters
      params = self.macro_identifier.extract_macro_parameters(macro)
      color = params.get('colour', params.get('color', 'grey'))
      title = params.get('title', '')

      # Map colors to emoji
      color_emoji = {
          'green': '🟢',
          'yellow': '🟡',
          'red': '🔴',
          'blue': '🔵',
          'grey': '⚪',
          'gray': '⚪',
          'purple': '🟣',
          'pink': '🔴',  # Assuming pink maps to red emoji as an example
          'orange': '🟠',
          'brown': '🟤',
          'black': '⚫',
          'white': '⚪'  # Ensure white is also mapped
      }.get(color.lower(), '⚪')  # Default to white circle if color unknown

      return f"({color_emoji} {title})" if title else f"{color_emoji}"
    except Exception as e:
      self.logger.error(f"Error parsing status macro: {e}")
      return "⚪ Unknown"  # Simplified fallback

  def parse_expand_macro(self, macro: Tag) -> str:
    """
    Parse a Confluence expand macro and convert it to Markdown.

    Args:
        macro: The BeautifulSoup Tag representing the expand macro.

    Returns:
        A Markdown representation of the expandable section.
    """
    try:
      # Extract content
      content_element = macro.find('ac:rich-text-body')
      if not content_element:
        return f"\n\nNo content found\n\n"

      # Convert content to Markdown
      content_html = str(content_element)
      content_md = markdownify.markdownify(content_html, heading_style="ATX")

      # Format as HTML details/summary (supported by many Markdown renderers)
      return f"\n\n{content_md}\n\n"
    except Exception as e:
      self.logger.error(f"Error parsing expand macro: {e}")
      return f"\n\nError parsing content\n\n"

  def parse_toc_macro(self, macro: Tag) -> str:
    """
    Parse a Confluence TOC macro and convert it to Markdown.

    Args:
        macro: The BeautifulSoup Tag representing the TOC macro.

    Returns:
        A Markdown placeholder for the TOC.
    """
    # For TOC, we just add a placeholder since the actual TOC will be generated
    # based on the final Markdown content
    return "<!-- Table of Contents placeholder -->\n\n"

  def parse_unknown_macro(self, macro: Tag) -> str:
    """
    Parse an unknown Confluence macro and provide a fallback representation.

    Args:
        macro: The BeautifulSoup Tag representing the unknown macro.

    Returns:
        A Markdown representation with information about the unknown macro.
    """
    try:
      macro_name = macro.get('ac:name', 'Unknown')
      params = self.macro_identifier.extract_macro_parameters(macro)

      # Create a comment with the macro information
      param_str = ", ".join([f"{k}='{v}'" for k, v in params.items()])
      comment = f"<!-- Unsupported Confluence Macro: {macro_name} {param_str} -->\n\n"

      # Try to extract any content
      content_element = macro.find('ac:rich-text-body')
      if content_element:
        content_html = str(content_element)
        content_md = markdownify.markdownify(content_html, heading_style="ATX")
        return f"{comment}**{macro_name} Macro Content:**\n\n{content_md}\n\n"
      else:
        return f"{comment}**{macro_name} Macro** _(Content could not be extracted)_\n\n"
    except Exception as e:
      self.logger.error(f"Error parsing unknown macro: {e}")
      return "<!-- Unsupported Confluence Macro -->\n\n**Unknown Macro** _(Content could not be extracted)_\n\n"

  async def parse_jira_macro(self, macro: Tag, jira_client: JiraClient = None) -> str:
    """
    Parse a JIRA macro and convert it to Markdown.
    Handles both JIRA issue links and JIRA tables.

    Args:
        macro: The BeautifulSoup Tag representing the JIRA macro.
        jira_client: Optional JiraClient implementation for resolving Jira issues.

    Returns:
        A Markdown representation of the JIRA issue or table.
    """
    try:
      if not jira_client:
        return "<!-- JIRA macro: No JIRA client provided -->\n\n**JIRA Reference** _(Could not be resolved without JIRA client)_\n\n"

      # Extract parameters
      params = self.macro_identifier.extract_macro_parameters(macro)

      # Check if this is a JIRA issue link (has a 'key' parameter)
      if 'key' in params:
        issue_key = params['key'].strip()

        # Get the issue URL
        issue_url = f"{jira_client.url}/browse/{issue_key}"

        # Add to JIRA issue links for metadata
        self.jira_issue_links.append({
          'issue_key': issue_key,
          'issue_url': issue_url
        })

        # Return a Markdown link
        return f"[{issue_key}]({issue_url})"

      # Check if this is a JQL table (has a 'jqlQuery' parameter)
      elif 'jqlQuery' in params:
        jql_query = params['jqlQuery'].strip()

        # Extract columns to display
        columns = params.get('columns', '').strip().split(',') if 'columns' in params else []

        # Extract column IDs
        column_ids = params.get('columnIds', '').strip().split(',') if 'columnIds' in params else []

        # Extract maximum issues
        max_issues = int(params.get('maximumIssues', '1000').strip())

        # Execute the JQL query
        issues = await jira_client.execute_jql(
            jql_query=jql_query,
            max_results=max_issues,
            fields=column_ids if column_ids else None
        )

        # Create an HTML table
        table_html = "<table border='1'>\n<thead>\n<tr>\n"

        # Use columns from the parameters if available, otherwise use column_ids
        display_columns = columns if columns else column_ids

        # Add table headers
        for col in display_columns:
          col_name = col.strip().capitalize()
          table_html += f"<th>{col_name}</th>\n"
        table_html += "</tr>\n</thead>\n<tbody>\n"

        # Add issue rows
        for issue in issues:
          table_html += "<tr>\n"

          # Track issue key and URL for metadata (do this once per issue, not per column)
          issue_key = issue.get('key', '')
          if issue_key:
            issue_url = f"{jira_client.url}/browse/{issue_key}"
            self.jira_issue_links.append({
              'issue_key': issue_key,
              'issue_url': issue_url
            })

          # Map column_ids to the fields in the issue
          for col_id in column_ids:
            col_id = col_id.strip()

            # Handle special field 'issuekey' for linking to the issue
            if col_id.lower() == 'issuekey':
              table_html += f"<td><a href='{issue_url}'>{issue_key}</a></td>\n"

            # Handle fields that might be nested objects
            elif col_id.lower() in ['project', 'issuetype', 'priority', 'status']:
              field_data = issue.get('fields', {}).get(col_id)
              if field_data and isinstance(field_data, dict):
                table_html += f"<td>{field_data.get('name', '')}</td>\n"
              else:
                table_html += f"<td>{str(field_data) if field_data else ''}</td>\n"

            # Handle components field (usually a list of component objects)
            elif col_id.lower() == 'components':
              components = issue.get('fields', {}).get('components', [])
              component_names = [c.get('name', '') for c in components if isinstance(c, dict)]
              table_html += f"<td>{', '.join(component_names)}</td>\n"

            # Handle regular fields
            else:
              field_data = issue.get('fields', {}).get(col_id, '')
              table_html += f"<td>{str(field_data) if field_data is not None else ''}</td>\n"

          table_html += "</tr>\n"

        table_html += "</tbody>\n</table>"

        # Add a comment with the JQL query
        jql_comment = f"<!-- JIRA Table: JQL Query: {jql_query} -->\n\n"

        return jql_comment + table_html

      else:
        # Unknown JIRA macro format
        return "<!-- Unknown JIRA macro format -->\n\n**JIRA Reference** _(Format not recognized)_\n\n"

    except Exception as e:
      self.logger.error(f"Error parsing JIRA macro: {e}")
      return f"<!-- Error parsing JIRA macro: {str(e)} -->\n\n**JIRA Reference Error** _(Could not be processed)_\n\n"

  def parse_view_file_macro(self, macro: Tag) -> str:
    """
    Parse a Confluence view-file macro for file attachments (non-video/non-image).

    Args:
        macro: The BeautifulSoup Tag representing the view-file macro.

    Returns:
        A Markdown representation of the file attachment.
    """
    try:
      # Extract the filename from ri:attachment
      attachment = macro.find('ri:attachment')
      if attachment:
        filename = attachment.get('ri:filename', '')
        if filename:
          # Add to discovered assets
          self.asset_links.append(filename)

          # Determine file type by extension
          extension = filename.split('.')[-1].lower() if '.' in filename else ''

          # Define file type mappings
          file_icons = {
              'pdf': '📄',
              'doc': '📝', 'docx': '📝',
              'xls': '📊', 'xlsx': '📊',
              'ppt': '📊', 'pptx': '📊',
              'txt': '📄', 'md': '📄',
              'json': '📄', 'xml': '📄',
              'csv': '📊',
              'zip': '📦', 'rar': '📦',
              'default': '📎'
          }

          icon = file_icons.get(extension, file_icons['default'])
          return f"\n\n[{icon} {filename}](ASSET_PLACEHOLDER_{filename})\n\n"

      return "\n\n[📎 File attachment](ASSET_PLACEHOLDER_unknown)\n\n"

    except Exception as e:
      self.logger.error(f"Error parsing view-file macro: {e}")
      return "\n\n[📎 File attachment (error processing)](ASSET_PLACEHOLDER_error)\n\n"

  def parse_iframe_macro(self, macro: Tag) -> str:
    """
    Parse a Confluence iframe macro and convert it to Markdown link format with original URL extraction.

    Args:
        macro: The BeautifulSoup Tag representing the iframe macro.

    Returns:
        A Markdown link representation of the iframe with extracted original URL.
    """
    try:
      # Get the URL from src parameter
      src_param = macro.find('ac:parameter', attrs={'ac:name': 'src'})
      url = ''
      if src_param:
        ri_url = src_param.find('ri:url')
        if ri_url:
          url = ri_url.get('ri:value', '')

      # Get the title parameter
      title_param = macro.find('ac:parameter', attrs={'ac:name': 'title'})
      title = title_param.get_text(strip=True) if title_param else "Iframe Content"

      if url:
        # Extract original URL from embed URL
        original_url = self._extract_original_url_from_iframe(url)

        # Add to external links for metadata
        self.external_links.append({
          'title': title,
          'url': original_url
        })

        return f"\n\n[{title}]({original_url})\n\n"
      else:
        return "\n\n[Iframe Content]()\n\n"

    except Exception as e:
      self.logger.error(f"Error parsing iframe macro: {e}")
      return "\n\n[Iframe Content]()\n\n"

  def _extract_original_url_from_iframe(self, embed_url: str) -> str:
    """
    Universal iframe to URL converter supporting major platforms.

    Args:
        embed_url: The iframe embed URL.

    Returns:
        The original URL or the embed URL if extraction fails.
    """
    try:
      parsed = urlparse(embed_url)
      domain = parsed.netloc.lower()
      path = parsed.path
      query = parse_qs(parsed.query)

      # YouTube
      if 'youtube.com' in domain and '/embed/' in path:
        video_id = Path(path).name
        return f"https://www.youtube.com/watch?v={video_id}"

      # Vimeo
      elif 'vimeo.com' in domain and '/video/' in path:
        video_id = Path(path).name
        return f"https://vimeo.com/{video_id}"

      # Google Maps
      elif 'google.com' in domain and 'maps/embed' in path:
        pb_param = query.get('pb', [''])[0]
        coord_pattern = r'!2d([-+]?\d*\.?\d+)!3d([-+]?\d*\.?\d+)'
        coord_match = re.search(coord_pattern, pb_param)
        if coord_match:
          longitude, latitude = coord_match.groups()
          return f"https://maps.google.com/?q={latitude},{longitude}"

      # Twitter
      elif 'platform.twitter.com' in domain or 'twitter.com' in domain:
        # Extract tweet ID or URL from embed
        if 'url=' in embed_url:
          tweet_url = re.search(r'url=([^&]+)', embed_url)
          if tweet_url:
            return unquote(tweet_url.group(1))

      # Instagram
      elif 'instagram.com' in domain and '/embed/' in path:
        post_id = path.split('/embed/')[-1].split('/')[0]
        return f"https://www.instagram.com/p/{post_id}/"

      # TikTok
      elif 'tiktok.com' in domain and '/embed/' in path:
        video_id = Path(path).name
        return f"https://www.tiktok.com/@user/video/{video_id}"

      # SoundCloud
      elif 'w.soundcloud.com' in domain:
        track_url = query.get('url', [''])[0]
        if track_url:
          return unquote(track_url)

      # Spotify
      elif 'open.spotify.com' in domain and '/embed/' in path:
        # Convert embed to regular Spotify URL
        clean_path = path.replace('/embed/', '/')
        return f"https://open.spotify.com{clean_path}"

      # Twitch
      elif 'player.twitch.tv' in domain:
        channel = query.get('channel', [''])[0]
        video = query.get('video', [''])[0]
        if channel:
          return f"https://www.twitch.tv/{channel}"
        elif video:
          return f"https://www.twitch.tv/videos/{video}"

      # CodePen
      elif 'codepen.io' in domain and '/embed/' in path:
        pen_url = path.replace('/embed/', '/')
        return f"https://codepen.io{pen_url}"

      # GitHub Gist
      elif 'gist.github.com' in domain:
        gist_url = embed_url.split('.js')[0]  # Remove .js extension
        return gist_url

      # JSFiddle
      elif 'jsfiddle.net' in domain and '/embedded/' in path:
        fiddle_url = path.replace('/embedded/', '/')
        return f"https://jsfiddle.net{fiddle_url}"

      # Generic iframe handling - try to extract src URL
      else:
        # Look for common embed patterns
        if '/embed/' in path:
          # Try converting /embed/ to regular path
          regular_path = path.replace('/embed/', '/')
          return f"{parsed.scheme}://{domain}{regular_path}"

        # If it's already an embed URL, try to get the source
        if 'src=' in embed_url or 'url=' in embed_url:
          src_match = re.search(r'(?:src|url)=([^&]+)', embed_url)
          if src_match:
            return unquote(src_match.group(1))

    except Exception as e:
      self.logger.error(f"Error extracting original URL from iframe: {e}")

    # Fallback: return original
    return embed_url


class EnhancedContentRenderer:
  """
  Renders complex Confluence elements with special handling.

  This class extends the basic HTML-to-Markdown conversion capabilities
  with specialized handling for complex Confluence elements like macros,
  tables with merged cells, and embedded content.
  """

  def __init__(self):
    """Initialize the EnhancedContentRenderer."""
    self.logger = logging.getLogger("EnhancedContentRenderer")
    self.macro_identifier = MacroIdentifier()
    self.external_links = []  # Store external links found during rendering
    self.user_mentions = []   # Store user mentions (account IDs) found during rendering
    self.internal_links = []  # Store internal page links found during rendering
    self.asset_links = []  # Store asset links found during rendering
    self.jira_issue_links = []  # Store JIRA issue links found during rendering
    self.user_info_cache = {}  # Cache for user information to avoid duplicate lookups
    self.macro_parser = None  # Initialize later after lists are ready

  async def render_content(self, html_content: str, page_id: str = None,
                          confluence_client: ConfluenceClient = None, jira_client: JiraClient = None, space_id: str = None) -> str:
    """
    Render HTML content with enhanced handling for Confluence-specific elements.

    Args:
        html_content: The HTML content to render.
        page_id: Optional page ID.
        confluence_client: Optional ConfluenceClient implementation for resolving internal links.
        jira_client: Optional JiraClient implementation for resolving Jira issues and JQL queries.

    Returns:
        str: The rendered Markdown content.
    """

    if not html_content:
      return ""

    try:
      # Reset stored data
      self.external_links = []
      self.user_mentions = []
      self.internal_links = []
      self.jira_issue_links = []
      self.asset_links = []

      # Initialize macro parser with reference to our lists
      self.macro_parser = MacroParser(self.asset_links, self.jira_issue_links, self.external_links)

      # Skip prepending title as H1 - the page title should be in the content already

      # Create BeautifulSoup object with html.parser parser which is faster than html.parser
      soup = BeautifulSoup(html_content, 'html.parser')
      # Also save just the formatted HTML content to a separate file for easier viewing

      # Process Confluence macros directly on the main soup object
      all_macro_tags_in_soup = soup.find_all('ac:structured-macro')

      for macro_tag in all_macro_tags_in_soup:
        # Ensure the tag is still part of the document (not already replaced by processing a parent or itself)
        if not macro_tag.parent:
          continue

        macro_name = macro_tag.get('ac:name', '')
        replacement_obj = None  # Can be a string or a list of nodes

        if macro_name == 'code':
          replacement_obj = self.macro_parser.parse_code_macro(macro_tag)
        elif macro_name in ['panel', 'info', 'note', 'warning', 'tip']:
          replacement_obj = self.macro_parser.parse_panel_macro(
              macro_tag, macro_name if macro_name != 'panel' else 'panel')
        elif macro_name == 'status':
          replacement_obj = self.macro_parser.parse_status_macro(macro_tag)
        elif macro_name == 'expand':
          replacement_obj = self.macro_parser.parse_expand_macro(macro_tag)
        elif macro_name == 'toc':
          replacement_obj = self.macro_parser.parse_toc_macro(macro_tag)
        elif macro_name == 'jira':
          # Process JIRA macro if JIRA client is provided
          if jira_client:
            replacement_obj = await self.macro_parser.parse_jira_macro(macro_tag, jira_client)
          else:
            replacement_obj = "<!-- JIRA macro: No JIRA client provided -->\n\n**JIRA Reference** _(Could not be resolved without JIRA client)_\n\n"
        elif macro_name == 'view-file':
          replacement_obj = self.macro_parser.parse_view_file_macro(macro_tag)
        elif macro_name == 'iframe':
          replacement_obj = self.macro_parser.parse_iframe_macro(macro_tag)
        else:  # unknown or other specific macros
          replacement_obj = self.macro_parser.parse_unknown_macro(macro_tag)

        new_nodes = []
        if isinstance(replacement_obj, str):
          # Parse the HTML/text string into new soup elements
          # Using 'html.parser' for fragments is sometimes more lenient or direct
          temp_soup = BeautifulSoup(replacement_obj, 'html.parser')
          # Extract all top-level elements from the parsed fragment
          extracted_children = list(temp_soup.contents)
          if len(extracted_children) == 1 and not isinstance(extracted_children[0], Tag) and not str(extracted_children[0]).strip():
            # If it's just whitespace or an empty NavigableString, make it an empty string to avoid issues.
            new_nodes.append(NavigableString(""))
          else:
            for node in extracted_children:
              # Detach from temp_soup before adding to main soup
              new_nodes.append(node.extract())
        elif isinstance(replacement_obj, Tag):  # If parser returns a Tag directly
          new_nodes = [replacement_obj.extract()]
        elif isinstance(replacement_obj, list):  # If parser returns a list of Tags/NavigableStrings
          new_nodes = [n.extract() if isinstance(n, Tag) else n for n in replacement_obj]

        if not new_nodes:  # Ensure there's something to replace with, even if empty
          new_nodes = [NavigableString("")]

        # Replace the macro_tag with the new_nodes
        current_insertion_point = macro_tag
        for new_node in new_nodes:
          current_insertion_point.insert_after(new_node)
          current_insertion_point = new_node

        macro_tag.decompose()  # Remove the original macro tag

      # Only process external links if there are any
      external_links = soup.find_all('a', href=True)
      if external_links:
        self._process_external_links_soup(soup)

      # Only process emoticons if there are any
      emoticons = soup.find_all('ac:emoticon')
      if emoticons:
        self._process_emoticons_soup(soup)

      # Process inline comments if there are any
      inline_comments = soup.find_all('ac:inline-comment-marker')
      if inline_comments:
        self._process_inline_comments_soup(soup)

      # Process time elements if there are any
      time_elements = soup.find_all('time')
      if time_elements:
        self._process_time_elements_soup(soup)

      # Process ADF note panels if there are any
      adf_panels = soup.find_all('ac:adf-extension')
      if adf_panels:
        self._process_adf_note_panels_soup(soup)

      # Process image and video elements if there are any
      ac_images = soup.find_all('ac:image')
      if ac_images:
        self._process_image_and_video_soup(soup)

      # Only process Confluence links if client is provided
      if confluence_client:
        # Extract and resolve user and page links (includes extraction)
        user_links = soup.find_all('ri:user')
        if user_links:
          await self._extract_user_links(soup, confluence_client)

        page_links = soup.find_all('ri:page')
        if page_links:
          await self._extract_page_links(soup, confluence_client, space_id)

      # Enhanced table processing with proper markdown conversion
      all_table_tags = soup.find_all('table')
      table_placeholders = {}
      placeholder_idx = 0

      if all_table_tags:

        # Get the HTML content as string to detect section levels
        html_content = str(soup)

        for table_tag in all_table_tags:
          placeholder = f"__TABLE_PLACEHOLDER_{placeholder_idx}__"
          table_html_str = str(table_tag)

          # Get content before this table to detect section level and text
          table_position = html_content.find(table_html_str)
          if table_position >= 0:
            content_before = html_content[:table_position]
            section_text, current_level = self.detect_section_level_and_text(content_before)
          else:
            section_text, current_level = None, 0

          # Convert table to enhanced markdown format
          markdown_table = self.convert_confluence_table_to_markdown(
              table_html_str, current_level, section_text=section_text)
          table_placeholders[placeholder] = markdown_table

          # Replace the table with a placeholder
          table_tag.replace_with(NavigableString(placeholder))
          placeholder_idx += 1

      # Get the HTML content with placeholders
      html_content_with_placeholders = str(soup)

      # Use markdownify to convert HTML to Markdown (excluding tables)

      # Use markdownify function without table processing since we handle tables separately
      markdown_content = markdownify.markdownify(
          html_content_with_placeholders,
          heading_style="atx",
          escape_underscores=False,  # Prevent escaping of our __PLACEHOLDER__
      )

      # Restore enhanced markdown tables from placeholders
      if table_placeholders:
        for placeholder, markdown_table in table_placeholders.items():
          if placeholder not in markdown_content:
            self.logger.warning(
                f"[TABLE_DEBUG] During restore: Placeholder '{placeholder}' not found in markdown_content. Table will be lost.")
          else:
            markdown_content = markdown_content.replace(placeholder, markdown_table)

      # Clean up excessive newlines
      markdown_content = re.sub(r'\\n{3,}', '\\n\\n', markdown_content)

      return markdown_content
    except Exception as e:
      self.logger.error(f"Error rendering content: {str(e)}")
      # Return original content or a simpler conversion as fallback
      return markdownify.markdownify(html_content, heading_style="atx")

  def get_discovered_assets(self) -> List[str]:
    """
    Get the list of asset filenames discovered during content rendering.

    Returns:
        List of unique asset filenames found in the content
    """
    # Return unique filenames to avoid duplicates
    return list(set(self.asset_links))

  def _is_jira_url_already_processed(self, url: str) -> bool:
    """
    Check if a URL is already processed in jira_issue_links to avoid duplication.

    Args:
        url: URL to check

    Returns:
        True if URL is already in jira_issue_links, False otherwise
    """
    for jira_link in self.jira_issue_links:
      if jira_link.get('issue_url') == url:
        return True
    return False

  def _process_external_links_soup(self, soup: BeautifulSoup) -> None:
    """
    Process external links directly in the soup object.
    More efficient version that doesn't require string conversion.
    """
    # Reset external links
    self.external_links = []

    links = soup.find_all('a', href=True)
    for link in links:
      href = link.get('href', '')

      # Skip if not an external link
      if not href or not (href.startswith('http://') or href.startswith('https://')):
        continue

      # Skip if this URL is already in jira_issue_links to avoid duplication
      if self._is_jira_url_already_processed(href):
        continue

      link_text = link.get_text(strip=True)

      # Add to external links for metadata
      self.external_links.append({
          'title': link_text,
          'url': href
      })

      # Format as markdown link [text](url)
      if 'drive.google.com' in href or 'docs.google.com' in href:
        # Handle Google Drive links specially with icons
        if '/document/' in href:
          icon_prefix = "📄 "
        elif '/spreadsheets/' in href or '/spreadsheet/' in href:
          icon_prefix = "📊 "
        elif '/presentation/' in href:
          icon_prefix = "🎭 "
        elif '/forms/' in href or '/form/' in href:
          icon_prefix = "📝 "
        else:
          icon_prefix = "📎 "

        if link_text == href or not link_text or link.get('data-card-appearance'):
          display_text = f"{icon_prefix}Google Drive Link"
        else:
          display_text = f"{icon_prefix}{link_text}"

        markdown_link = f"[{display_text}]({href})"
      else:
        # Regular external links
        if link_text == href or not link_text:
          display_text = href
        else:
          display_text = link_text

        markdown_link = f"[{display_text}]({href})"

      # Replace the link with markdown format
      link.replace_with(NavigableString(markdown_link))

  def _process_emoticons_soup(self, soup: BeautifulSoup) -> None:
    """
    Process emoticons directly in the soup object.
    More efficient version that doesn't require string conversion.
    """
    emoticons = soup.find_all('ac:emoticon')
    for emoticon in emoticons:
      # Get the emoji fallback first (this is the actual emoji)
      emoji_fallback = emoticon.get('ac:emoji-fallback', '')

      # If no fallback, try shortname without colons
      if not emoji_fallback:
        emoji_shortname = emoticon.get('ac:emoji-shortname', '')
        if emoji_shortname:
          # Remove colons from shortname like :white_check_mark: -> white_check_mark
          emoji_fallback = emoji_shortname.strip(':')

      # If still no emoji, use the name as fallback
      if not emoji_fallback:
        name_attr = emoticon.get('ac:name', 'unknown')
        emoji_fallback = f":{name_attr}:"

      # Replace with the emoji
      emoticon.replace_with(NavigableString(emoji_fallback))

  def _process_inline_comments_soup(self, soup: BeautifulSoup) -> None:
    """
    Process inline comment markers directly in the soup object.
    Removes the ac:inline-comment-marker tags while preserving the content inside.
    """
    inline_comments = soup.find_all('ac:inline-comment-marker')
    for comment_marker in inline_comments:
      try:
        # Get the text content inside the marker
        content = comment_marker.get_text(strip=False)
        if content:
          # Replace the marker with just the content
          comment_marker.replace_with(NavigableString(content))
        else:
          # If no content, just remove the marker
          comment_marker.decompose()
      except Exception as e:
        self.logger.error(f"Error processing inline comment marker: {e}")
        # Fallback: just extract the text content
        text_content = comment_marker.get_text(strip=False)
        if text_content:
          comment_marker.replace_with(NavigableString(text_content))
        else:
          comment_marker.decompose()

  def _process_time_elements_soup(self, soup: BeautifulSoup) -> None:
    """
    Process time elements directly in the soup object.
    Extracts text from datetime attribute and replaces the time tag.
    """
    time_elements = soup.find_all('time')
    for time_element in time_elements:
      try:
        datetime_attr = time_element.get('datetime', '')
        if datetime_attr:
          time_element.replace_with(NavigableString(datetime_attr))
        else:
          # Fallback to text content if no datetime attribute
          time_element.replace_with(NavigableString(time_element.get_text(strip=True)))
      except Exception as e:
        self.logger.error(f"Error processing time element: {e}")
        time_element.replace_with(NavigableString(time_element.get_text(strip=True)))

  def _process_adf_note_panels_soup(self, soup: BeautifulSoup) -> None:
    """
    Process ADF note panels directly in the soup object.
    Converts ac:adf-extension elements with panel nodes to markdown format.
    """
    adf_extensions = soup.find_all('ac:adf-extension')
    for adf_extension in adf_extensions:
      try:
        # Check if this extension contains a panel node
        adf_node = adf_extension.find('ac:adf-node', {'type': 'panel'})
        if adf_node:
          # Extract content from ac:adf-content
          content_element = adf_node.find('ac:adf-content')
          if content_element:
            # Convert content to text
            content_text = content_element.get_text(strip=True)
            # Format as note panel with note symbol
            note_content = f"> 📝 {content_text}"
            # Replace the extension with the note content
            adf_extension.replace_with(NavigableString(note_content))
          else:
            adf_extension.replace_with(NavigableString("> ⚠️  Note panel content not found"))
      except Exception as e:
        self.logger.error(f"Error processing ADF note panel: {e}")
        adf_extension.replace_with(NavigableString("> ⚠️  Error processing note panel"))

  def _process_image_and_video_soup(self, soup: BeautifulSoup) -> None:
    """
    Process image and video elements (ac:image with ri:attachment) directly in the soup object.
    Handles both image and video file types.
    """
    ac_images = soup.find_all('ac:image')
    for ac_image in ac_images:
      try:
        # Find the attachment inside ac:image
        attachment = ac_image.find('ri:attachment')
        if attachment:
          filename = attachment.get('ri:filename', '')
          if filename:
            # Add to discovered assets
            self.asset_links.append(filename)

            # Determine if it's an image or video based on file extension
            extension = filename.split('.')[-1].lower() if '.' in filename else ''

            # Define image and video extensions
            image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'tiff']
            video_extensions = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']

            if extension in image_extensions:
              replacement = f"\n\n[🖼️ {filename}](ASSET_PLACEHOLDER_{filename})\n\n"
            elif extension in video_extensions:
              replacement = f"\n\n[🎬 {filename}](ASSET_PLACEHOLDER_{filename})\n\n"
            else:
              # Fallback for unknown extensions
              replacement = f"\n\n[📎 {filename}](ASSET_PLACEHOLDER_{filename})\n\n"

            ac_image.replace_with(NavigableString(replacement))
          else:
            ac_image.replace_with(NavigableString("\n\n[🖼️ Image attachment](ASSET_PLACEHOLDER_unknown)\n\n"))

      except Exception as e:
        self.logger.error(f"Error processing ac:image element: {e}")
        ac_image.replace_with(NavigableString("\n\n[🖼️ Image attachment (error processing)](ASSET_PLACEHOLDER_error)\n\n"))



  async def _extract_user_links(self, soup: BeautifulSoup, confluence_client: ConfluenceClient) -> None:
    """
    Extract and resolve user links by fetching user information and updating the HTML.

    Args:
        soup: The BeautifulSoup object to process.
        confluence_client: The Confluence client for fetching user information.
    """
    # Find all user links and extract account IDs
    user_links = soup.find_all('ri:user')
    account_ids = []

    for user_link in user_links:
      account_id = user_link.get('ri:account-id')
      if account_id:
        account_ids.append(account_id)

    # Get unique account IDs
    unique_account_ids = list(set(account_ids))

    if not unique_account_ids:
      return

    try:
      # Get user information in bulk
      users_info = await confluence_client.get_users_by_account_ids(unique_account_ids)

      # Update the user_info_cache
      self.user_info_cache.update(users_info)

      # Store user mentions with complete information
      for account_id in unique_account_ids:
        if account_id in users_info:
          user_info = users_info[account_id]
          self.user_mentions.append({
            'account_id': account_id,
            'display_name': user_info.get('displayName', 'Unknown User'),
            'profile_url': user_info.get('profileUrl', '#')
          })

      # Find all ac:link elements with ri:user and replace them
      user_link_elements = soup.find_all('ac:link', recursive=True)

      for link_element in user_link_elements:
        user_element = link_element.find('ri:user')
        if not user_element:
          continue

        account_id = user_element.get('ri:account-id')
        if not account_id or account_id not in users_info:
          continue

        # Get user info
        user_info = users_info[account_id]
        display_name = user_info.get('displayName', 'Unknown User')
        profile_url = user_info.get('profileUrl', '#')

        # Create markdown format link [display_name](profile_url)
        markdown_link = f"[{display_name}]({profile_url})"

        # Replace the ac:link with the markdown link
        link_element.replace_with(NavigableString(markdown_link))

    except Exception as e:
      self.logger.error(f"Error resolving user links: {e}")

  async def _extract_page_links(self, soup: BeautifulSoup, confluence_client: ConfluenceClient, space_id: str) -> None:
    """
    Extract and resolve page links by fetching page information and updating the HTML.

    Args:
        soup: The BeautifulSoup object to process.
        confluence_client: The Confluence client for fetching page information.
        space_id: The current space ID for context.
    """
    # Find all page links and extract titles
    page_links = soup.find_all('ri:page')
    page_titles = []

    for page_link in page_links:
      title = page_link.get('ri:content-title')
      if title:
        page_titles.append(title)

    # Track processed links to avoid duplicates
    processed_links = set()

    # Find all ac:link elements with ri:page
    page_link_elements = soup.find_all('ac:link', recursive=True)

    for link_element in page_link_elements:
      page_element = link_element.find('ri:page')
      if not page_element:
        continue

      title = page_element.get('ri:content-title')
      if not title:
        continue

      # Skip if we've processed this link already
      if title in processed_links:
        continue

      processed_links.add(title)

      try:
        page_data = await confluence_client.find_page_by_title(space_id, title)

        if page_data:
          # Store page link with complete information
          self.internal_links.append({
            'page_id': page_data.get('id'),
            'page_title': page_data.get('title', title),
            'page_url': page_data.get('url')
          })

          # Get the page URL
          page_url = page_data.get('url')

          # Get the link text (prefer the ac:link-body if available)
          link_body = link_element.find('ac:link-body')
          if link_body and link_body.string:
            link_text = link_body.string.strip()
          else:
            link_text = title

          # Replace all occurrences of this page link with markdown format
          for page_link in soup.find_all('ac:link'):
            page_ri = page_link.find('ri:page')
            if page_ri and page_ri.get('ri:content-title') == title:
              # Get the link body text for this specific link
              specific_link_body = page_link.find('ac:link-body')
              if specific_link_body and specific_link_body.string:
                specific_text = specific_link_body.string.strip()
                markdown_link = f"[{specific_text}]({page_url})"
              else:
                markdown_link = f"[{link_text}]({page_url})"

              # Replace with markdown format
              page_link.replace_with(NavigableString(markdown_link))

      except Exception as e:
        self.logger.warning(
            f"Error resolving page link '{title}': {e}")
        continue

  # ============================================
  # Enhanced Table Processing Functions
  # ============================================

  # Constants for table processing
  MARKDOWN_INDENT = "    "  # 4 spaces

  # Compile regex patterns for better performance
  TRIPLE_NEWLINE_PATTERN = re.compile(r'\n{3,}')
  HEADING_PATTERN = re.compile(r'^(#{1,6})\s+', re.MULTILINE)

  def convert_confluence_table_to_markdown(self, html_content, current_section_level=0, section_text=None):
    """
    Convert Confluence HTML table to structured markdown format

    Args:
        html_content: HTML string containing the table
        current_section_level: Current heading level (0 for root, 1 for #, 2 for ##, etc.)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')

    if not table:
      return html_content

    # Extract table metadata - single pass through rows
    rows = table.find_all('tr')
    if not rows:
      return html_content

    # Detect header row and analyze structure in one pass
    has_header_row, headers, num_columns, header_rows_count, colspan_count, rowspan_count = self.detect_header_and_structure(
        rows)
    num_rows = len(rows)

    # Get detailed span location information
    colspan_locations, rowspan_locations = self._get_span_locations(rows)

    # Generate enhanced table metadata
    metadata_lines = []
    metadata_lines.append("\n\n<!-- TABLE_START -->")

    # Table Summary
    summary_parts = [f"{num_columns} columns", f"{num_rows} rows"]
    if has_header_row:
      summary_parts.append("has header row")
    else:
      summary_parts.append("no header row")

    # Add span information with locations
    span_info = []
    if colspan_locations:
      colspan_details = [f"row {r} col {c} (span {s})" for r, c, s in colspan_locations]
      span_info.append(f"{len(colspan_locations)} colspans ({', '.join(colspan_details)})")
    if rowspan_locations:
      rowspan_details = [f"row {r} col {c} (span {s})" for r, c, s in rowspan_locations]
      span_info.append(f"{len(rowspan_locations)} rowspans ({', '.join(rowspan_details)})")

    if span_info:
      summary_parts.append(f"contains {', '.join(span_info)}")
    else:
      summary_parts.append("no spans")

    metadata_lines.append(f"<!-- Table Summary: {', '.join(summary_parts)} -->")

    # Use the section text passed from the caller (already detected efficiently)
    if section_text:
      metadata_lines.append(
          f"<!-- Table Section: {section_text} (H{current_section_level} level) -->")
    else:
      # Fallback to level-based description if no section text provided
      section_context = self._generate_section_context(current_section_level)
      metadata_lines.append(f"<!-- Table Section: {section_context} -->")

    # Clean headers for processing
    import json
    clean_column_headers = [self._clean_header_text(h) for h in headers]

    # Row Headers (collect first)
    row_headers = []
    start_row_index = header_rows_count if has_header_row else 0  # Skip all header rows
    for row in rows[start_row_index:]:
      first_cell = row.find(['td', 'th'])
      if first_cell:
        text = first_cell.get_text(separator=' ')
        # Clean row header text to remove newlines
        cleaned_text = self._clean_header_text(text)
        if cleaned_text:  # Increased length for row identifiers
          # Take first few words if it's long
          words = cleaned_text.split()
          if len(words) > 5:
            cleaned_text = ' '.join(words[:5]) + '...'
          row_headers.append(cleaned_text)

    # Table Purpose (NEW)
    # Get section text for context
    section_text_for_purpose = section_text if 'section_text' in locals() else None
    table_purpose = self._infer_table_purpose(
        clean_column_headers, row_headers[:3], section_text_for_purpose)
    if table_purpose:
      metadata_lines.append(f"<!-- Table Purpose: {table_purpose} -->")

    # Column Headers
    metadata_lines.append(
        f"<!-- Column Headers: {json.dumps(clean_column_headers, ensure_ascii=False)} -->")

    # Row Headers
    metadata_lines.append(f"<!-- Row Headers: {json.dumps(row_headers, ensure_ascii=False)} -->")

    # Table Complexity (NEW)
    complexity = self._calculate_table_complexity(
        num_rows, num_columns, colspan_count, rowspan_count, has_header_row)
    metadata_lines.append(f"<!-- Table Complexity: {complexity} -->")

    # Combine metadata
    table_start_metadata = "\n".join(metadata_lines)

    # Process data rows with colspan/rowspan handling
    markdown_sections = []

    # Calculate heading levels
    row_heading_level = current_section_level + 1
    column_heading_level = current_section_level + 2
    row_heading_prefix = "#" * row_heading_level
    column_heading_prefix = "#" * column_heading_level

    # Build a matrix to track cell content and spans
    table_matrix = self.build_table_matrix(rows, headers, has_header_row, header_rows_count)

    # Generate markdown sections with content duplication for spans
    for row_idx, row_data in enumerate(table_matrix):
      if row_idx < header_rows_count and has_header_row:  # Skip all header rows
        continue

      row_id = row_data.get('row_id', str(row_idx))

      # Create section header with dynamic level
      markdown_sections.append(f"{row_heading_prefix} {row_id}")
      markdown_sections.append("")

      # Process each column for this row (including first column)
      for col_idx, header in enumerate(headers):
        if header.strip() and col_idx < len(row_data['cells']):
          cell_content = row_data['cells'][col_idx].get('content', '')

          if cell_content.strip():
            markdown_sections.append(f"{column_heading_prefix} {header}")
            markdown_sections.append(cell_content)
            markdown_sections.append("")

    # Combine everything with TABLE_END marker
    markdown_content = "\n".join(markdown_sections)
    table_end_metadata = "<!-- TABLE_END -->"

    result = table_start_metadata + "\n\n" + markdown_content + "\n\n" + table_end_metadata
    return result

  def detect_header_and_structure(self, rows):
    """
    Detect header row and analyze table structure in a single pass

    Returns:
        tuple: (has_header_row, headers, num_columns, header_rows_count, colspan_count, rowspan_count)
    """
    if not rows:
      return False, [], 0, 0, 0, 0

    first_row = rows[0]
    cells = first_row.find_all(['th', 'td'])

    if not cells:
      return False, [], 0, 0, 0, 0

    # Initialize span counters
    colspan_count = 0
    rowspan_count = 0

    # Check header criteria and count spans simultaneously
    has_all_th = True
    has_data_attributes = False

    for cell in cells:
      # Header detection
      if cell.name != 'th':
        has_all_th = False
      # Check all the data attributes that disqualify headers
      if (cell.get('data-cell-background') or cell.get('data-highlight-colour')):
        has_data_attributes = True

      # Count spans across all rows (do this for all rows)
      colspan = cell.get('colspan')
      if colspan and int(colspan) > 1:
        colspan_count += 1

      rowspan = cell.get('rowspan')
      if rowspan and int(rowspan) > 1:
        rowspan_count += 1

    # Count spans in remaining rows
    for row in rows[1:]:
      row_cells = row.find_all(['td', 'th'])
      for cell in row_cells:
        colspan = cell.get('colspan')
        if colspan and int(colspan) > 1:
          colspan_count += 1

        rowspan = cell.get('rowspan')
        if rowspan and int(rowspan) > 1:
          rowspan_count += 1

    is_header_row = has_all_th and not has_data_attributes

    if not is_header_row:
      # Calculate actual number of columns accounting for colspans in first row
      actual_num_columns = sum(int(cell.get('colspan', 1)) for cell in cells)
      # Generate default headers
      headers = [f"Table Data Column {i}" for i in range(1, actual_num_columns + 1)]
      return False, headers, actual_num_columns, 0, colspan_count, rowspan_count

    # Process header row
    header_rows_count = 1
    max_rowspan = max(int(cell.get('rowspan', 1)) for cell in cells)
    if max_rowspan > 1 and len(rows) > 1:
      header_rows_count = max_rowspan

    # Calculate actual number of columns accounting for colspans
    actual_num_columns = sum(int(cell.get('colspan', 1)) for cell in cells)

    # Build headers efficiently
    if header_rows_count > 1:
      headers = self.build_header_matrix(rows[:header_rows_count])
    else:
      headers = []
      for cell in cells:
        # Process cell content once
        cell_copy = BeautifulSoup(str(cell), 'html.parser')
        self._process_element_recursively(cell_copy)
        header_text = cell_copy.get_text(separator=' ')
        # Clean header text to remove newlines
        cleaned_header = self._clean_header_text(header_text)

        # Add header text for each column this cell spans
        colspan = int(cell.get('colspan', 1))
        for _ in range(colspan):
          headers.append(cleaned_header)

    return is_header_row, headers, actual_num_columns, header_rows_count, colspan_count, rowspan_count

  def build_header_matrix(self, header_rows):
    """
    Build a matrix for header rows that properly handles colspan and rowspan
    Returns the final header structure
    """
    if not header_rows:
      return []

    # First, determine the total number of columns
    max_cols = 0
    for row in header_rows:
      cells = row.find_all(['th', 'td'])
      col_count = sum(int(cell.get('colspan', 1)) for cell in cells)
      max_cols = max(max_cols, col_count)

    # Initialize matrix
    matrix = []
    for _ in range(len(header_rows)):
      matrix.append([None] * max_cols)

    # Fill the matrix
    for row_idx, row in enumerate(header_rows):
      cells = row.find_all(['th', 'td'])
      col_pos = 0

      for cell in cells:
        # Find next available position
        while col_pos < max_cols and matrix[row_idx][col_pos] is not None:
          col_pos += 1

        if col_pos >= max_cols:
          break

        colspan = int(cell.get('colspan', 1))
        rowspan = int(cell.get('rowspan', 1))

        # Process cell content to handle links, formatting, etc.
        cell_copy = BeautifulSoup(str(cell), 'html.parser')
        self._process_element_recursively(cell_copy)
        header_text = cell_copy.get_text(separator=' ')
        # Clean header text to remove newlines
        cell_text = self._clean_header_text(header_text)

        # Fill all cells covered by this cell's span
        for r in range(row_idx, min(row_idx + rowspan, len(header_rows))):
          for c in range(col_pos, min(col_pos + colspan, max_cols)):
            if r == row_idx and c == col_pos:
              # This is the main cell
              matrix[r][c] = cell_text
            else:
              # This is covered by span
              matrix[r][c] = f"__SPAN__{cell_text}"

        col_pos += colspan

    # Build final headers by combining multi-row headers
    final_headers = []
    for col in range(max_cols):
      header_parts = []
      for row in range(len(header_rows)):
        cell_value = matrix[row][col]
        if cell_value and not cell_value.startswith('__SPAN__'):
          header_parts.append(cell_value)
        elif cell_value and cell_value.startswith('__SPAN__'):
          # This column is covered by a span from above
          span_value = cell_value.replace('__SPAN__', '')
          if span_value not in header_parts:
            header_parts.append(span_value)

      # Combine header parts
      if header_parts:
        combined_header = ' - '.join(header_parts)
        # Clean the final combined header as well
        cleaned_combined = self._clean_header_text(combined_header)
        final_headers.append(cleaned_combined)
      else:
        final_headers.append(f"Column {col + 1}")

    return final_headers

  def _clean_header_text(self, header_text):
    """
    Clean header text by replacing all newlines with single spaces and removing extra whitespace.
    Headers should be single-line text without line breaks.
    Also handles proper emoji display.
    """
    if not header_text:
      return header_text

    # Handle emoji encoding issues - ensure proper UTF-8 encoding
    if isinstance(header_text, str):
      # Ensure the text is properly encoded as UTF-8
      try:
        cleaned = header_text.encode('utf-8').decode('utf-8')
      except (UnicodeEncodeError, UnicodeDecodeError):
        cleaned = header_text
    else:
      cleaned = str(header_text)

    # Replace all types of newlines with single spaces
    cleaned = re.sub(r'\n+', ' ', cleaned)

    # Remove extra whitespace (multiple spaces become single space)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned

  def _get_span_locations(self, rows):
    """
    Get detailed information about colspan and rowspan locations.
    Returns lists of tuples (row_num, col_num) for cells with spans.
    """
    colspan_locations = []
    rowspan_locations = []

    for row_idx, row in enumerate(rows):
      cells = row.find_all(['td', 'th'])
      col_idx = 0

      for cell in cells:
        colspan = int(cell.get('colspan', 1))
        rowspan = int(cell.get('rowspan', 1))

        if colspan > 1:
          colspan_locations.append((row_idx + 1, col_idx + 1, colspan))  # 1-based indexing
        if rowspan > 1:
          rowspan_locations.append((row_idx + 1, col_idx + 1, rowspan))  # 1-based indexing

        col_idx += colspan

    return colspan_locations, rowspan_locations

  def _calculate_table_complexity(self, num_rows, num_columns, colspan_count, rowspan_count, has_header_row):
    """
    Calculate table complexity based on various factors.
    Returns: 'Simple', 'Medium', or 'Complex'
    """
    complexity_score = 0

    # Base complexity from size
    total_cells = num_rows * num_columns
    if total_cells > 50:
      complexity_score += 2
    elif total_cells > 20:
      complexity_score += 1

    # Complexity from spans
    if colspan_count > 0 or rowspan_count > 0:
      complexity_score += 1
      if (colspan_count + rowspan_count) > 3:
        complexity_score += 1

    # Header complexity
    if not has_header_row:
      complexity_score += 1  # No headers make it harder to understand

    # Large table dimensions
    if num_columns > 6 or num_rows > 10:
      complexity_score += 1

    # Determine complexity level
    if complexity_score <= 1:
      return "Simple"
    elif complexity_score <= 3:
      return "Medium"
    else:
      return "Complex"

  def _infer_table_purpose(self, headers, row_samples, section_text):
    """
    Try to infer the table purpose based on headers, content, and section context.
    Returns a descriptive purpose string.
    """
    if not headers:
      return None

    # Convert headers to lowercase for analysis
    header_text = ' '.join(headers).lower()

    # Common table purposes based on header patterns
    purpose_patterns = {
        'deployment': ['deployment', 'deploy', 'release', 'version', 'service'],
        'checklist': ['checklist', 'status', 'done', 'completed', 'verified'],
        'comparison': ['vs', 'versus', 'compare', 'difference', 'before', 'after'],
        'pricing': ['price', 'cost', 'fee', 'amount', 'payment'],
        'schedule': ['date', 'time', 'schedule', 'timeline', 'deadline'],
        'contact': ['name', 'email', 'phone', 'contact', 'person'],
        'configuration': ['config', 'setting', 'parameter', 'value', 'option'],
        'metrics': ['metric', 'measurement', 'count', 'total', 'average'],
        'requirements': ['requirement', 'criteria', 'specification', 'rule'],
        'issues': ['issue', 'bug', 'error', 'problem', 'ticket']
    }

    # Check for purpose patterns in headers
    for purpose, keywords in purpose_patterns.items():
      if any(keyword in header_text for keyword in keywords):
        return f"{purpose.title()} data"

    # Check section context for additional clues
    if section_text:
      section_lower = section_text.lower()
      for purpose, keywords in purpose_patterns.items():
        if any(keyword in section_lower for keyword in keywords):
          return f"{purpose.title()} table"

    # Generic purposes based on column count
    if len(headers) <= 2:
      return "Simple data listing"
    elif len(headers) <= 4:
      return "Data comparison table"
    else:
      return "Detailed information matrix"

  def _generate_section_context(self, current_section_level):
    """
    Generate section context description based on the detected section level.
    """
    if current_section_level == 0:
      return "Document root level"
    elif current_section_level == 1:
      return "Main section (H1 level)"
    elif current_section_level == 2:
      return "Subsection (H2 level)"
    elif current_section_level == 3:
      return "Sub-subsection (H3 level)"
    else:
      return f"Deep subsection (H{current_section_level} level)"

  def build_table_matrix(self, rows, headers, has_header_row, header_rows_count=1):
    """
    Build a matrix representation of the table handling colspan and rowspan
    by duplicating content in all affected cells
    """
    if not rows:
      return []

    table_matrix = []
    num_cols = len(headers)

    # Initialize matrix with empty cells
    for row_idx in range(len(rows)):
      row_data = {
          'row_id': '',
          'cells': [{'content': '', 'original': False} for _ in range(num_cols)]
      }
      table_matrix.append(row_data)

    # Process each row
    for row_idx, row in enumerate(rows):
      if row_idx < header_rows_count and has_header_row:  # Skip all header rows
        continue

      cells = row.find_all(['td', 'th'])
      if not cells:
        continue

      # Get row identifier from first cell - extract heading only
      actual_row_number = row_idx - header_rows_count + 1 if has_header_row else row_idx + 1
      if cells:
        row_text = cells[0].get_text(separator=' ')
        # Clean row identifier text to remove newlines
        cleaned_row_text = self._clean_header_text(row_text)
        table_matrix[row_idx]['row_id'] = cleaned_row_text
      else:
        table_matrix[row_idx]['row_id'] = f"Table Data Row {actual_row_number}"

      # Track current column position (accounting for spans from previous cells)
      current_col = 0

      for cell in cells:
        # Skip to next available column (in case previous cells had colspan)
        while (current_col < num_cols and
               table_matrix[row_idx]['cells'][current_col].get('content')):
          current_col += 1

        if current_col >= num_cols:
          break

        # Get cell properties
        colspan = int(cell.get('colspan', 1))
        rowspan = int(cell.get('rowspan', 1))
        content = self.process_cell_content(cell)

        # Fill all cells affected by this colspan/rowspan with the same content
        for r in range(row_idx, min(row_idx + rowspan, len(rows))):
          for c in range(current_col, min(current_col + colspan, num_cols)):
            if r < len(table_matrix) and c < len(table_matrix[r]['cells']):
              table_matrix[r]['cells'][c]['content'] = content
              table_matrix[r]['cells'][c]['original'] = (r == row_idx and c == current_col)
              table_matrix[r]['cells'][c]['colspan'] = colspan if r == row_idx else 1
              table_matrix[r]['cells'][c]['rowspan'] = rowspan if c == current_col else 1

        # Move to next column position
        current_col += colspan

    return table_matrix

  def process_cell_content(self, cell):
    """
    Process individual cell content, converting HTML to markdown
    """
    # Convert directly without creating a new BeautifulSoup object
    # This is more efficient than creating a copy
    self.convert_html_to_markdown_recursively(cell)

    # Get text content and clean it up
    content = cell.get_text(separator='\n\n')

    # Clean up extra whitespace - use compiled pattern
    content = self.TRIPLE_NEWLINE_PATTERN.sub('\n\n', content.strip())

    return content

  def convert_html_to_markdown_recursively(self, soup_element):
    """
    Recursively convert HTML elements to markdown format in a single pass
    Handles all element types including nested structures
    """
    # Find top-level lists more efficiently
    all_lists = soup_element.find_all(['ol', 'ul'])
    top_level_lists = [lst for lst in all_lists if not any(
        p.name in ['ol', 'ul'] for p in lst.parents)]

    # Process each top-level list
    for list_elem in top_level_lists:
      if list_elem.parent:  # Make sure it's still in the tree
        markdown_text = self.convert_single_list_to_markdown(list_elem)
        list_elem.replace_with(markdown_text)

    # Process all other elements recursively
    self._process_element_recursively(soup_element)

  def _process_element_recursively(self, element):
    """
    Recursively process an element and all its children to convert HTML to markdown
    """
    if not hasattr(element, 'find_all'):
      return

    # Get all elements to process, excluding lists which are handled separately
    known_elements = ['strong', 'b', 'em', 'i', 'code', 'a', 'br',
                      'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ol', 'ul', 'li']

    # Find all elements and sort them by depth (deepest first) to avoid processing conflicts
    all_elements = element.find_all()

    # Group elements by type, but process from deepest to shallowest
    def get_element_depth(elem):
      depth = 0
      parent = elem.parent
      while parent and parent != element:
        depth += 1
        parent = parent.parent
      return depth

    # Sort all elements by depth (deepest first)
    sorted_elements = sorted(all_elements, key=get_element_depth, reverse=True)

    # Group elements by type
    elements_to_process = {
        'formatting': [elem for elem in sorted_elements if elem.name in ['strong', 'b', 'em', 'i', 'code']],
        'links': [elem for elem in sorted_elements if elem.name == 'a'],
        'breaks': [elem for elem in sorted_elements if elem.name == 'br'],
        'blocks': [elem for elem in sorted_elements if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']],
        'other': [elem for elem in sorted_elements if elem.name not in known_elements]
    }

    # Convert formatting elements (deepest first)
    for elem in elements_to_process['formatting']:
      if elem.parent:  # Still in tree
        text = elem.get_text().strip()
        # Skip elements with only whitespace
        if not text:
          elem.decompose()
          continue

        if elem.name in ['strong', 'b']:
          elem.replace_with(f"**{text}**")
        elif elem.name in ['em', 'i']:
          elem.replace_with(f"*{text}*")
        elif elem.name == 'code':
          elem.replace_with(f"`{text}`")

    # Convert links (deepest first)
    for link in elements_to_process['links']:
      if link.parent:  # Still in tree
        href = link.get('href', '')
        text = link.get_text(strip=True)
        # Skip elements with only whitespace
        if not text:
          link.decompose()
          continue
        if href and text:
          link.replace_with(f"[{text}]({href})")
        elif text:
          # If no href but has text, just use the text
          link.replace_with(text)

    # Handle BR tags (deepest first)
    for br in elements_to_process['breaks']:
      if br.parent:  # Still in tree
        br.replace_with('\n\n')

    # Handle other undefined elements first (deepest first) - just extract text if it exists
    for elem in elements_to_process['other']:
      if elem.parent:  # Still in tree
        text = elem.get_text()
        if text:
          # If element has text content, replace with the text
          elem.replace_with(text)
        else:
          # If element has only whitespace, remove it
          elem.decompose()

    # Handle block elements last (deepest first)
    for block in elements_to_process['blocks']:
      if block.parent:  # Still in tree
        self._convert_block_element(block, '\n\n')

  def _convert_block_element(self, element, suffix):
    """
    Convert a block element (p, h1-h6) to markdown, preserving inner formatting
    """
    content_parts = []
    for child in element.children:
      if hasattr(child, 'get_text'):
        content_parts.append(str(child))
      else:
        content_parts.append(str(child))

    inner_content = ''.join(content_parts).strip()
    # Only keep elements with meaningful content (not just whitespace)
    if inner_content and inner_content != '\n' and inner_content != '\n\n':
      element.replace_with(f'{inner_content}{suffix}')
    else:
      element.decompose()  # Remove empty elements or elements with only whitespace

  def convert_single_list_to_markdown(self, list_element, indent_level=0):
    """
    Convert a single HTML list to markdown format with proper nesting
    Returns the markdown text representation
    """
    if not list_element:
      return ""

    is_ordered = list_element.name == 'ol'
    items = list_element.find_all('li', recursive=False)  # Only direct children

    markdown_lines = []

    for i, item in enumerate(items, 1):
      # Create proper indentation
      indent = self.MARKDOWN_INDENT * indent_level

      # Create the list marker
      if is_ordered:
        marker = f"{i}."
      else:
        marker = "-"

      # Process this item's direct text content and nested lists separately
      item_copy = BeautifulSoup(str(item), 'html.parser')

      # Extract direct text (not from nested lists)
      direct_text_parts = []
      nested_lists = []

      for child in item_copy.li.children:
        if hasattr(child, 'name'):
          if child.name in ['ol', 'ul']:
            # This is a nested list
            nested_lists.append(child)
          else:
            # This is other content - process it using unified conversion
            if hasattr(child, 'find_all'):
              # Use the unified processing for this child element
              self._process_element_recursively(child)

              # Get text using innerHTML to preserve inline formatting
              content_parts = []
              for grandchild in child.children:
                if hasattr(grandchild, 'get_text'):
                  content_parts.append(str(grandchild))
                else:
                  content_parts.append(str(grandchild))

              text = ''.join(content_parts).strip()
            else:
              # This is a text node
              text = str(child)

            if text.strip():
              direct_text_parts.append(text.strip())
        else:
          # This is direct text
          text = str(child).strip()
          if text:
            direct_text_parts.append(text)

      # Combine direct text more efficiently
      if direct_text_parts:
        combined_text = '\n'.join(direct_text_parts)
        text_lines = [line.strip() for line in combined_text.split('\n') if line.strip()]

        if text_lines:
          # First line with marker
          markdown_lines.append(f"{indent}{marker} {text_lines[0]}")

          # Subsequent lines with content indentation
          content_indent = indent + self.MARKDOWN_INDENT
          markdown_lines.extend(f"{content_indent}{line}" for line in text_lines[1:])
      else:
        markdown_lines.append(f"{indent}{marker}")

      # Process nested lists recursively
      for nested_list in nested_lists:
        nested_markdown = self.convert_single_list_to_markdown(nested_list, indent_level + 1)
        if nested_markdown:
          markdown_lines.extend(line for line in nested_markdown.split('\n') if line.strip())

    return "\n\n".join(markdown_lines)

  def detect_section_level_and_text(self, content_before_table):
    """
    Detect both the current section level and section text from content before the table.
    Returns (section_text, section_level) tuple.
    """
    # First try to find HTML heading tags
    section_text, section_level = self._extract_html_headings(content_before_table, text_only=False)
    if section_text:
      return section_text, section_level

    # Fallback: try markdown headings (for cases where content is already converted)
    matches = self.HEADING_PATTERN.findall(content_before_table)
    if matches:
      level = len(matches[-1])
      # Try to extract text from the last markdown heading
      lines = content_before_table.split('\n')
      for line in reversed(lines):
        if line.strip().startswith('#'):
          text = line.strip().lstrip('#').strip()
          return text, level
      return f"Section Level {level}", level

    return None, 0  # No headings found

  def _extract_html_headings(self, html_content, text_only=False):
    """
    Unified function to extract heading information from HTML content.
    Consolidates 4 similar functions into one efficient implementation.
    """
    try:
      from bs4 import BeautifulSoup
      soup = BeautifulSoup(html_content, 'html.parser')
      heading_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

      if text_only:
        return [int(tag.name[1]) for tag in heading_tags]

      if heading_tags:
        last_heading = heading_tags[-1]
        heading_text = self._clean_header_text(last_heading.get_text(separator=' '))
        level = int(last_heading.name[1])
        return heading_text, level

      return None, 0

    except (ImportError, Exception):
      # Regex fallback
      import re
      heading_pattern = re.compile(r'<h([1-6])[^>]*>(.*?)</h[1-6]>', re.IGNORECASE | re.DOTALL)
      matches = list(heading_pattern.finditer(html_content))

      if text_only:
        return [int(match.group(1)) for match in matches]

      if matches:
        last_match = matches[-1]
        level = int(last_match.group(1))
        text_only_content = re.sub(r'<[^>]+>', ' ', last_match.group(2))
        heading_text = self._clean_header_text(text_only_content)
        return heading_text, level

      return None, 0
