"""
Confluence element handlers for processing special HTML elements.

This package contains handler classes for converting Confluence-specific HTML elements
(user mentions, page links, images, emoticons, etc.) into Markdown format.
Each handler extends BaseElementHandler and implements element-specific processing logic.

Handlers process the HTML document after macro expansion and operate on BeautifulSoup objects.
All handlers implement graceful degradation to ensure processing continues even on failures.
"""
