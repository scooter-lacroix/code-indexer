from typing import List, Optional, Any, Dict, Union, Literal
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FileMetadata:
    path: str
    hash: str
    last_modified: Optional[str] = None
    size: Optional[int] = None

@dataclass
class StoreFile:
    external_id: Optional[str]
    metadata: Optional[FileMetadata]

@dataclass
class ChunkType:
    type: Literal["text", "image_url", "audio_url", "video_url"]
    text: Optional[str] = None
    score: float = 0.0
    metadata: Optional[FileMetadata] = None
    chunk_index: Optional[int] = None
    generated_metadata: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None # For web results

@dataclass
class SearchResponse:
    data: List[ChunkType]

@dataclass
class AskResponse:
    answer: str
    sources: List[ChunkType]

@dataclass
class StoreInfo:
    name: str
    description: str
    created_at: str
    updated_at: str
    counts: Dict[str, int]

@dataclass
class UploadFileOptions:
    external_id: str
    overwrite: bool = True
    metadata: Optional[FileMetadata] = None

@dataclass
class SearchOptions:
    rerank: bool = True
    top_k: int = 10
    include_web: bool = False
    content: bool = False # Show content in result
    use_zoekt: bool = False # Use Zoekt strategy if available
