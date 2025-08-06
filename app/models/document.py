from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    XLSX = "xlsx"
    XLS = "xls"

class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

class DocumentBase(BaseModel):
    title: str
    file_name: str
    document_type: DocumentType
    content: str
    file_size: int
    status: DocumentStatus = DocumentStatus.PROCESSING
    tags: List[str] = []
    description: Optional[str] = None
    embedding: Optional[List[float]] = None
    chunk_count: int = 0
    metadata: Dict[str, Any] = {}

class DocumentCreate(DocumentBase):
    workspace_id: str

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[DocumentStatus] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None

class DocumentInDB(DocumentBase):
    id: str = Field(alias="_id")
    workspace_id: str
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0

class Document(DocumentBase):
    id: str = Field(alias="_id")
    workspace_id: str
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0

class DocumentChunk(BaseModel):
    id: str = Field(alias="_id")
    document_id: str
    workspace_id: str
    content: str
    chunk_index: int
    embedding: List[float]
    metadata: Dict[str, Any] = {}
    created_at: datetime

class DocumentSearch(BaseModel):
    query: str
    workspace_id: str
    limit: int = 5
    similarity_threshold: float = 0.6
    document_types: Optional[List[DocumentType]] = None
    tags: Optional[List[str]] = None

class SearchResult(BaseModel):
    document: Document
    chunks: List[DocumentChunk]
    similarity_score: float
    relevance_score: float