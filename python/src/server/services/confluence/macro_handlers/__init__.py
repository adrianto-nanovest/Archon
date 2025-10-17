"""
Confluence macro handlers for processing structured macros in Confluence Storage Format HTML.

This package contains handler classes for converting Confluence-specific macros
(code blocks, panels, JIRA issues, attachments, etc.) into Markdown format for RAG retrieval.
Each handler extends BaseMacroHandler and implements macro-specific processing logic.

Handlers are registered in ConfluenceProcessor and called during the macro expansion pass.
"""
