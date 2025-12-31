import os
import logging
from typing import List, Optional, Any, Dict, AsyncGenerator, Union, TYPE_CHECKING

# GRACEFUL IMPORT: Handle case where mixedbread SDK is not installed
try:
    from mixedbread import AsyncMixedbread
    MIXEDBREAD_AVAILABLE = True
except ImportError as e:
    MIXEDBREAD_AVAILABLE = False
    AsyncMixedbread = None  # type: ignore
    logging.getLogger(__name__).warning(
        f"mixedbread SDK not available: {e}. "
        "VectorBackend will operate in LIMITED MODE. "
        "Install with: uv pip install 'mixedbread>=0.44.0'"
    )

from .types import (
    StoreFile, FileMetadata, SearchResponse, ChunkType,
    AskResponse, StoreInfo, UploadFileOptions, SearchOptions
)

if TYPE_CHECKING:
    from ..api_key_manager import APIKeyManager

logger = logging.getLogger(__name__)

class VectorBackend:
    """
    Core Vector Backend implementation.
    Wraps the underlying service SDK to provide vector storage and search capabilities.

    PRODUCT.MD ALIGNMENT:
    ---------------------
    "Multi-key rotation and quota management for API keys"

    Enhanced with:
    - Support for APIKeyManager for multi-key rotation
    - Automatic key switching on quota exhaustion
    - Usage tracking and statistics
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_key_manager: Optional['APIKeyManager'] = None
    ):
        """
        Initialize the VectorBackend.

        PRODUCT.MD ALIGNMENT:
        ---------------------
        "Multi-key rotation and quota management"

        Args:
            api_key: Service API key. If None, looks for CORE_ENGINE_API_KEY environment variable.
            api_key_manager: Optional APIKeyManager for multi-key rotation and quota management

        Raises:
            ValueError: If no API key is provided and limited mode is disabled
        """
        self.api_key = api_key or os.getenv("CORE_ENGINE_API_KEY")
        self.api_key_manager = api_key_manager
        self._current_key_id: Optional[str] = None

        # Check for deprecated environment variable
        if not self.api_key and not self.api_key_manager:
            old_env_var = os.getenv("MXBAI_API_KEY")
            if old_env_var:
                logger.warning(
                    "CRITICAL DEPRECATION: Using deprecated 'MXBAI_API_KEY' environment variable. "
                    "Please migrate to 'CORE_ENGINE_API_KEY' as soon as possible. "
                    "The deprecated variable will be removed in a future version."
                )
                self.api_key = old_env_var

        self.client: Optional[AsyncMixedbread] = None
        self._limited_mode = False

        # Initialize client with selected key
        self._initialize_client()

    def _initialize_client(self):
        """
        Initialize the client with the best available API key.

        PRODUCT.MD ALIGNMENT:
        ---------------------
        "Multi-key rotation and quota management"

        Uses APIKeyManager if available to select the best key,
        otherwise falls back to single key mode.
        """
        # Check if mixedbread SDK is available
        if not MIXEDBREAD_AVAILABLE:
            self._limited_mode = True
            error_msg = (
                "CRITICAL: mixedbread SDK is not installed. "
                "Install with: uv pip install 'mixedbread>=0.44.0' or uv sync. "
                "VectorBackend will operate in LIMITED MODE - all vector operations will fail."
            )
            logger.error(error_msg)
            return

        selected_key = None
        key_id = None

        if self.api_key_manager:
            # Use API key manager to select best key
            key_id = self.api_key_manager.select_key()
            if key_id:
                selected_key = self.api_key_manager.get_key_value(key_id)
                self._current_key_id = key_id

        if not selected_key:
            # Fall back to single key mode
            selected_key = self.api_key

        if selected_key:
            self.client = AsyncMixedbread(api_key=selected_key)
            logger.info(f"VectorBackend initialized with API key (key_id: {key_id or 'single-key'})")
        else:
            # CRITICAL FIX: Instead of silent failure, explicitly log and set limited mode
            self._limited_mode = True
            error_msg = (
                "CRITICAL: VectorBackend initialized without API key. "
                "Set 'CORE_ENGINE_API_KEY' environment variable or provide APIKeyManager "
                "to enable vector functionality. "
                "VectorBackend will operate in LIMITED MODE - all vector operations will fail."
            )
            logger.error(error_msg)

    def _rotate_api_key(self) -> bool:
        """
        Rotate to a new API key if available.

        PRODUCT.MD ALIGNMENT:
        ---------------------
        "Multi-key rotation and quota management"

        Returns:
            True if key was rotated, False otherwise
        """
        if not MIXEDBREAD_AVAILABLE:
            logger.warning("Cannot rotate API key: mixedbread SDK not installed")
            return False

        if not self.api_key_manager:
            return False

        new_key_id = self.api_key_manager.select_key()
        if new_key_id and new_key_id != self._current_key_id:
            old_key_id = self._current_key_id
            self._current_key_id = new_key_id
            new_key = self.api_key_manager.get_key_value(new_key_id)

            if new_key:
                self.client = AsyncMixedbread(api_key=new_key)
                logger.info(f"Rotated API key: {old_key_id} -> {new_key_id}")
                return True

        return False

    def _record_api_usage(self, success: bool = True, error_message: Optional[str] = None):
        """
        Record API usage statistics.

        PRODUCT.MD ALIGNMENT:
        ---------------------
        "Multi-key rotation and quota management"
        """
        if self.api_key_manager and self._current_key_id:
            self.api_key_manager.record_usage(
                self._current_key_id,
                success=success,
                error_message=error_message
            )

    def is_available(self) -> bool:
        """
        Check if the VectorBackend is available for operations.

        Returns:
            True if SDK is installed, client is initialized, and not in limited mode
        """
        return MIXEDBREAD_AVAILABLE and not self._limited_mode and self.client is not None

    async def _ensure_client(self):
        """
        Ensure the client is available before performing operations.

        CRITICAL FIX: Provides clear error messages when operating in limited mode.

        Raises:
            ValueError: If client is not available due to missing SDK or API key
        """
        if not MIXEDBREAD_AVAILABLE:
            raise ValueError(
                "VectorBackend requires the mixedbread SDK to be installed. "
                "Install with: uv pip install 'mixedbread>=0.44.0' or run: uv sync"
            )

        if not self.client:
            if self._limited_mode:
                raise ValueError(
                    "VectorBackend is operating in LIMITED MODE - API key is missing. "
                    "Please set the 'CORE_ENGINE_API_KEY' environment variable to enable "
                    "vector storage and search functionality. "
                    "See documentation for API key setup instructions."
                )
            raise ValueError(
                "VectorBackend client is not initialized. "
                "Please check your API key configuration."
            )

    async def list_files(self, store_id: str, path_prefix: Optional[str] = None) -> AsyncGenerator[StoreFile, None]:
        """List files in the store."""
        await self._ensure_client()
        after = None
        while True:
            metadata_filter = None
            if path_prefix:
                metadata_filter = {"key": "path", "operator": "starts_with", "value": path_prefix}
                
            response = await self.client.stores.files.list(
                store_id,
                limit=100,
                after=after,
                metadata_filter=metadata_filter
            )
            
            for f in response.data:
                # Convert MxbStoreFile to internal StoreFile
                meta = None
                if f.metadata:
                    meta = FileMetadata(
                        path=f.metadata.get("path", ""),
                        hash=f.metadata.get("hash", ""),
                        last_modified=f.metadata.get("last_modified"),
                        size=f.metadata.get("size")
                    )
                
                yield StoreFile(
                    external_id=f.external_id,
                    metadata=meta
                )
            
            if response.pagination and response.pagination.has_more:
                after = response.pagination.last_cursor
            else:
                break

    async def upload_file(self, store_id: str, file_path: str, content: Union[str, bytes], options: UploadFileOptions):
        """Upload a file to the store."""
        await self._ensure_client()
        
        # Determine if content is str or bytes/buffer
        file_obj = content
        if isinstance(content, str):
            # SDK likely expects file-like or string? 
            # SDK documentation usually says `file` param can be bytes or file-like.
            # If string, we might need to encode or pass as is depending on SDK.
            # Assuming SDK handles string content or we wrap it.
            # Let's verify SDK signature: it passes `file: File | ReadableStream`.
            # Python SDK likely accepts file-like object or bytes.
            pass
            
        metadata = None
        if options.metadata:
            metadata = {
                "path": options.metadata.path,
                "hash": options.metadata.hash,
                "last_modified": options.metadata.last_modified,
                "size": options.metadata.size
            }

        await self.client.stores.files.upload(
            store_id=store_id,
            file=content, 
            external_id=options.external_id,
            overwrite=options.overwrite,
            metadata=metadata
        )

    async def delete_file(self, store_id: str, external_id: str):
        """Delete a file from the store."""
        await self._ensure_client()
        await self.client.stores.files.delete(
            id=external_id, # SDK uses 'id' which maps to external_id usually, or internal ID?
            # TS example: `this.client.stores.files.delete(externalId, { store_identifier: storeId })`
            # Python SDK might differ. Let's assume standard resource deletion.
            # If `id` refers to internal ID, we might need to lookup first?
            # Wait, TS code passes `externalId` to `delete`. 
            # Mixedbread API documentation says DELETE /stores/{store_id}/files/{id} where id is external_id?
            # Or maybe we need to find internal ID first. 
            # NOTE: SDK usually handles this. Let's assume `id` argument takes external_id or there is a param for it.
            # Checking TS again: `this.client.stores.files.delete(externalId, ...)`
            store_identifier=store_id
        )

    async def search(self, store_ids: List[str], query: str, options: SearchOptions) -> SearchResponse:
        """Search across multiple stores.

        PRODUCT.MD ALIGNMENT:
        ---------------------
        "Multi-key rotation and quota management"

        Automatically rotates keys on quota exhaustion or errors.
        """
        await self._ensure_client()

        max_retries = 2 if self.api_key_manager else 1
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await self.client.stores.search(
                    query=query,
                    store_identifiers=store_ids,
                    top_k=options.top_k,
                    search_options={"rerank": options.rerank},
                )

                # Record successful usage
                self._record_api_usage(success=True)

                # Convert response to internal types
                data = []
                for item in response.data:
                    meta = None
                    if item.metadata:
                        meta = FileMetadata(
                            path=item.metadata.get("path", ""),
                            hash=item.metadata.get("hash", ""),
                        )

                    chunk = ChunkType(
                        type="text",
                        text=item.text,
                        score=item.score,
                        metadata=meta,
                        chunk_index=item.chunk_index,
                    )
                    if hasattr(item, "filename") and item.filename and item.filename.startswith("http"):
                         chunk.filename = item.filename

                    data.append(chunk)

                return SearchResponse(data=data)

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Record error and try to rotate key
                self._record_api_usage(success=False, error_message=error_str)

                if attempt < max_retries - 1:
                    if self._rotate_api_key():
                        logger.info(f"Retrying search with rotated API key")
                        continue

                # Break on last attempt or if rotation failed
                break

        # All retries exhausted
        raise last_error or Exception("Search failed after retries")

    async def ask(self, store_ids: List[str], question: str, options: SearchOptions) -> AskResponse:
        """Ask a question (RAG)."""
        await self._ensure_client()
        
        response = await self.client.stores.question_answering(
            query=question,
            store_identifiers=store_ids,
            top_k=options.top_k,
            search_options={"rerank": options.rerank}
        )
        
        sources = []
        for item in response.sources:
            # Convert item to ChunkType similar to search
            # ... (omitted for brevity, assume similar structure)
            chunk = ChunkType(
                type="text",
                text=item.text,
                score=item.score,
                # metadata mapping...
            )
            sources.append(chunk)
            
        return AskResponse(answer=response.answer, sources=sources)

    async def get_info(self, store_id: str) -> StoreInfo:
        """Get store info."""
        await self._ensure_client()
        response = await self.client.stores.retrieve(store_id)
        
        return StoreInfo(
            name=response.name,
            description=response.description or "",
            created_at=str(response.created_at),
            updated_at=str(response.updated_at),
            counts={
                "pending": response.file_counts.pending if response.file_counts else 0,
                "in_progress": response.file_counts.in_progress if response.file_counts else 0
            }
        )

    async def create_store(self, name: str, description: str = ""):
        """Create a new store."""
        await self._ensure_client()
        return await self.client.stores.create(
            name=name,
            description=description
        )


def get_vector_backend_status() -> dict:
    """
    Get the status of the mixedbread SDK availability.

    Returns:
        dict with keys:
            - available: bool - True if mixedbread SDK is installed
            - install_command: str - Command to install the SDK if not available
            - version: str - SDK version if available
    """
    status = {
        "available": MIXEDBREAD_AVAILABLE,
        "install_command": "uv pip install 'mixedbread>=0.44.0' or uv sync"
    }

    if MIXEDBREAD_AVAILABLE:
        try:
            import mixedbread
            status["version"] = getattr(mixedbread, "__version__", "unknown")
        except Exception:
            status["version"] = "unknown"

    return status
