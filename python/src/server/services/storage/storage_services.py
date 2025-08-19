"""
Storage Services

This module contains all storage service classes that handle document and data storage operations.
These services extend the base storage functionality with specific implementations.
"""

from typing import Any

from fastapi import WebSocket

from ...config.logfire_config import get_logger, safe_span
from .base_storage_service import BaseStorageService
from .document_storage_service import add_documents_to_supabase

logger = get_logger(__name__)


class DocumentStorageService(BaseStorageService):
    """Service for handling document uploads with progress reporting."""

    async def upload_document(
        self,
        file_content: str,
        filename: str,
        source_id: str,
        knowledge_type: str = "documentation",
        tags: list[str] | None = None,
        websocket: WebSocket | None = None,
        progress_callback: Any | None = None,
        cancellation_check: Any | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Upload and process a document file with progress reporting.

        Args:
            file_content: Document content as text
            filename: Name of the file
            source_id: Source identifier
            knowledge_type: Type of knowledge
            tags: Optional list of tags
            websocket: Optional WebSocket for progress
            progress_callback: Optional callback for progress
            cancellation_check: Optional callback to check for cancellation

        Returns:
            Tuple of (success, result_dict)
        """
        logger.info(f"Document upload starting: {filename} as {knowledge_type} knowledge")
        
        with safe_span(
            "upload_document",
            filename=filename,
            source_id=source_id,
            content_length=len(file_content),
        ) as span:
            try:
                # Progress reporting helper
                async def report_progress(message: str, percentage: int, batch_info: dict = None):
                    if websocket:
                        data = {
                            "type": "upload_progress",
                            "filename": filename,
                            "progress": percentage,
                            "message": message,
                        }
                        if batch_info:
                            data.update(batch_info)
                        await websocket.send_json(data)
                    if progress_callback:
                        await progress_callback(message, percentage, batch_info)

                await report_progress("Starting document processing...", 10)

                # Check for cancellation
                if cancellation_check and await cancellation_check():
                    logger.info(f"Upload cancelled for {filename}")
                    return False, {"error": "Upload cancelled by user"}

                # Use base class chunking
                chunks = await self.smart_chunk_text_async(
                    file_content,
                    chunk_size=5000,
                    progress_callback=lambda msg, pct: report_progress(
                        f"Chunking: {msg}", 10 + float(pct) * 0.2
                    ),
                )

                if not chunks:
                    raise ValueError("No content could be extracted from the document")

                await report_progress("Preparing document chunks...", 30)

                # Check for cancellation
                if cancellation_check and await cancellation_check():
                    logger.info(f"Upload cancelled for {filename}")
                    return False, {"error": "Upload cancelled by user"}

                # Prepare data for storage
                doc_url = f"file://{filename}"
                urls = []
                chunk_numbers = []
                contents = []
                metadatas = []
                total_word_count = 0

                # Process chunks with metadata
                for i, chunk in enumerate(chunks):
                    # Check for cancellation periodically
                    if cancellation_check and await cancellation_check():
                        logger.info(f"Upload cancelled for {filename}")
                        return False, {"error": "Upload cancelled by user"}

                    # Use base class metadata extraction
                    meta = self.extract_metadata(
                        chunk,
                        {
                            "chunk_index": i,
                            "url": doc_url,
                            "source": source_id,
                            "source_id": source_id,
                            "knowledge_type": knowledge_type,
                            "filename": filename,
                        },
                    )

                    if tags:
                        meta["tags"] = tags

                    urls.append(doc_url)
                    chunk_numbers.append(i)
                    contents.append(chunk)
                    metadatas.append(meta)
                    total_word_count += len(chunk.split())

                await report_progress("Generating embeddings and storing...", 60)

                # Store documents in database
                success, docs_result = await add_documents_to_supabase(
                    urls=urls,
                    chunk_numbers=chunk_numbers,
                    contents=contents,
                    metadatas=metadatas,
                    source_id=source_id,
                    knowledge_type=knowledge_type,
                    cancellation_check=cancellation_check,
                    progress_callback=lambda msg, pct: report_progress(
                        f"Storage: {msg}", 60 + float(pct) * 0.35
                    ),
                )

                if not success:
                    raise ValueError(f"Failed to store documents: {docs_result.get('error', 'Unknown error')}")

                await report_progress("Document upload completed successfully!", 100)

                # Set span attributes
                span.set_attribute("chunks_processed", len(chunks))
                span.set_attribute("total_word_count", total_word_count)
                span.set_attribute("documents_stored", docs_result.get("documents_stored", 0))

                logger.info(
                    f"Document upload completed: {filename} - {len(chunks)} chunks, {total_word_count} words"
                )

                return True, {
                    "message": f"Document '{filename}' uploaded successfully",
                    "filename": filename,
                    "source_id": source_id,
                    "knowledge_type": knowledge_type,
                    "chunks_processed": len(chunks),
                    "total_word_count": total_word_count,
                    "documents_stored": docs_result.get("documents_stored", 0),
                }

            except Exception as e:
                logger.error(f"Error uploading document {filename}: {e}")
                span.set_attribute("error", str(e))
                
                # Send error progress if we can
                try:
                    await report_progress(f"Error: {str(e)}", -1)
                except Exception:
                    pass  # Don't let progress reporting errors mask the original error
                    
                return False, {
                    "error": f"Failed to upload document: {str(e)}",
                    "filename": filename,
                }


class CodeStorageService(BaseStorageService):
    """Service for handling code storage operations."""

    async def store_code_examples(
        self,
        code_examples: list[dict[str, Any]],
        source_id: str,
        progress_callback: Any | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Store code examples in the database.

        Args:
            code_examples: List of code example dictionaries
            source_id: Source identifier
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            logger.info(f"Storing {len(code_examples)} code examples for source: {source_id}")

            if progress_callback:
                await progress_callback("Storing code examples...", 0)

            # Import the code storage service function
            from .code_storage_service import store_code_examples

            # Store the code examples
            success, result = await store_code_examples(
                code_examples, source_id, progress_callback
            )

            if progress_callback:
                await progress_callback("Code examples stored successfully", 100)

            return success, result

        except Exception as e:
            logger.error(f"Error in store_code_examples: {e}")
            if progress_callback:
                await progress_callback(f"Error storing code examples: {e}", -1)
            return False, {"error": str(e)}