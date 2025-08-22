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
                            "source_type": "file",  # FIX: Mark as file upload
                            "filename": filename,
                        },
                    )

                    if tags:
                        meta["tags"] = tags

                    urls.append(doc_url)
                    chunk_numbers.append(i)
                    contents.append(chunk)
                    metadatas.append(meta)
                    total_word_count += meta.get("word_count", 0)

                await report_progress("Updating source information...", 50)

                # Create URL to full document mapping
                url_to_full_document = {doc_url: file_content}

                # Update source information
                from ...utils import extract_source_summary, update_source_info

                source_summary = await self.threading_service.run_cpu_intensive(
                    extract_source_summary, source_id, file_content[:5000]
                )

                logger.info(f"Updating source info for {source_id} with knowledge_type={knowledge_type}")
                await self.threading_service.run_io_bound(
                    update_source_info,
                    self.supabase_client,
                    source_id,
                    source_summary,
                    total_word_count,
                    file_content[:1000],  # content for title generation
                    knowledge_type,      # FIX: Pass knowledge_type parameter!
                    tags,               # FIX: Pass tags parameter!
                )

                await report_progress("Storing document chunks...", 70)

                # Store documents
                await add_documents_to_supabase(
                    client=self.supabase_client,
                    urls=urls,
                    chunk_numbers=chunk_numbers,
                    contents=contents,
                    metadatas=metadatas,
                    url_to_full_document=url_to_full_document,
                    batch_size=15,
                    progress_callback=progress_callback,
                    enable_parallel_batches=True,
                    provider=None,  # Use configured provider
                    cancellation_check=cancellation_check,
                )

                await report_progress("Document upload completed!", 100)

                result = {
                    "chunks_stored": len(chunks),
                    "total_word_count": total_word_count,
                    "source_id": source_id,
                    "filename": filename,
                }

                span.set_attribute("success", True)
                span.set_attribute("chunks_stored", len(chunks))
                span.set_attribute("total_word_count", total_word_count)

                logger.info(
                    f"Document upload completed successfully: filename={filename}, chunks_stored={len(chunks)}, total_word_count={total_word_count}"
                )

                return True, result

            except Exception as e:
                span.set_attribute("success", False)
                span.set_attribute("error", str(e))
                logger.error(f"Error uploading document: {e}")

                if websocket:
                    await websocket.send_json({
                        "type": "upload_error",
                        "error": str(e),
                        "filename": filename,
                    })

                return False, {"error": f"Error uploading document: {str(e)}"}

    async def store_documents(self, documents: list[dict[str, Any]], **kwargs) -> dict[str, Any]:
        """
        Store multiple documents. Implementation of abstract method.

        Args:
            documents: List of documents to store
            **kwargs: Additional options (websocket, progress_callback, etc.)

        Returns:
            Storage result
        """
        results = []
        for doc in documents:
            success, result = await self.upload_document(
                file_content=doc["content"],
                filename=doc["filename"],
                source_id=doc.get("source_id", "upload"),
                knowledge_type=doc.get("knowledge_type", "documentation"),
                tags=doc.get("tags"),
                websocket=kwargs.get("websocket"),
                progress_callback=kwargs.get("progress_callback"),
                cancellation_check=kwargs.get("cancellation_check"),
            )
            results.append(result)

        return {
            "success": all(r.get("chunks_stored", 0) > 0 for r in results),
            "documents_processed": len(documents),
            "results": results,
        }

    async def process_document(self, document: dict[str, Any], **kwargs) -> dict[str, Any]:
        """
        Process a single document. Implementation of abstract method.

        Args:
            document: Document to process
            **kwargs: Additional processing options

        Returns:
            Processed document with metadata
        """
        # Extract text content
        content = document.get("content", "")

        # Chunk the content
        chunks = await self.smart_chunk_text_async(content)

        # Extract metadata for each chunk
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            meta = self.extract_metadata(
                chunk, {"chunk_index": i, "source": document.get("source", "unknown")}
            )
            processed_chunks.append({"content": chunk, "metadata": meta})

        return {
            "chunks": processed_chunks,
            "total_chunks": len(chunks),
            "source": document.get("source"),
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

    async def store_documents(self, documents: list[dict[str, Any]], **kwargs) -> dict[str, Any]:
        """
        Store documents. Implementation of abstract method.

        Args:
            documents: List of documents to store
            **kwargs: Additional options

        Returns:
            Storage result
        """
        # For code storage, we treat documents as code examples
        code_examples = [
            {
                "code": doc.get("content", ""),
                "language": doc.get("language", "unknown"),
                "context": doc.get("context", ""),
            }
            for doc in documents
        ]

        source_id = kwargs.get("source_id", "code_storage")
        progress_callback = kwargs.get("progress_callback")

        success, result = await self.store_code_examples(
            code_examples, source_id, progress_callback
        )

        return {
            "success": success,
            "documents_processed": len(documents),
            "result": result,
        }

    async def process_document(self, document: dict[str, Any], **kwargs) -> dict[str, Any]:
        """
        Process a document as code. Implementation of abstract method.

        Args:
            document: Document to process
            **kwargs: Additional options

        Returns:
            Processed document
        """
        content = document.get("content", "")

        # For code, we don't chunk but treat as single unit
        return {
            "chunks": [{"content": content, "metadata": {"type": "code"}}],
            "total_chunks": 1,
            "source": document.get("source"),
        }
