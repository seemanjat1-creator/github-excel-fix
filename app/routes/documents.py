from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
from app.models.user import User
from app.models.document import Document, DocumentSearch, SearchResult, DocumentUpdate
from app.auth.auth_handler import get_current_active_user, verify_workspace_access
from app.services.document_service import document_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/workspace/{workspace_id}", response_model=List[Document])
async def get_workspace_documents(
    workspace_id: str,
    document_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    """Get all documents for a workspace with filtering"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    documents = await document_service.get_workspace_documents(workspace_id)
    
    # Apply filters
    if document_type:
        documents = [doc for doc in documents if doc.document_type == document_type]
    
    if status:
        documents = [doc for doc in documents if doc.status == status]
    
    if search:
        search_lower = search.lower()
        documents = [
            doc for doc in documents 
            if search_lower in doc.title.lower() or 
               search_lower in doc.file_name.lower() or
               search_lower in (doc.description or "").lower()
        ]
    
    # Apply pagination
    total = len(documents)
    documents = documents[offset:offset + limit]
    
    return documents

@router.get("/workspace/{workspace_id}/stats")
async def get_workspace_document_stats(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get document statistics for workspace"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    return await document_service.get_document_stats(workspace_id)

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get document by ID"""
    # First get the document to check workspace access
    from app.database import get_database
    from bson import ObjectId
    
    db = get_database()
    doc_data = await db.documents.find_one({"_id": ObjectId(document_id)})
    
    if not doc_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    workspace_id = str(doc_data["workspace_id"])
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to document"
        )
    
    return await document_service.get_document_by_id(document_id, workspace_id)

@router.post("/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    current_user: User = Depends(get_current_active_user)
):
    """Upload document to workspace (supports PDF, DOCX, TXT, XLSX, XLS)"""
    logger.info(f"Document upload request from user {current_user.id} for workspace {workspace_id}")
    logger.info(f"File details: {file.filename}, size: {file.size if hasattr(file, 'size') else 'unknown'}")
    logger.info(f"File type: {file.content_type}")
    
    if not await verify_workspace_access(current_user, workspace_id):
        logger.warning(f"Access denied for user {current_user.id} to workspace {workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    return await document_service.upload_document(
        file=file,
        workspace_id=workspace_id,
        title=title,
        description=description,
        tags=tag_list
    )

@router.put("/{document_id}", response_model=Document)
async def update_document(
    document_id: str,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update document metadata"""
    # First get the document to check workspace access
    from app.database import get_database
    from bson import ObjectId
    
    db = get_database()
    doc_data = await db.documents.find_one({"_id": ObjectId(document_id)})
    
    if not doc_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    workspace_id = str(doc_data["workspace_id"])
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to document"
        )
    
    # Only allow certain updates
    update_dict = {}
    if update_data.title is not None:
        update_dict["title"] = update_data.title
    if update_data.description is not None:
        update_dict["description"] = update_data.description
    if update_data.tags is not None:
        update_dict["tags"] = update_data.tags
    
    updated_doc = await document_service.update_document(document_id, workspace_id, update_dict)
    if not updated_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return updated_doc

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete document"""
    # First get the document to check workspace access
    from app.database import get_database
    from bson import ObjectId
    
    db = get_database()
    doc_data = await db.documents.find_one({"_id": ObjectId(document_id)})
    
    if not doc_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    workspace_id = str(doc_data["workspace_id"])
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to document"
        )
    
    success = await document_service.delete_document(document_id, workspace_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {"message": "Document deleted successfully"}

@router.post("/search", response_model=List[SearchResult])
async def search_documents(
    search_request: DocumentSearch,
    current_user: User = Depends(get_current_active_user)
):
    """Advanced vector search in documents"""
    if not await verify_workspace_access(current_user, search_request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    return await document_service.search_documents(search_request)

@router.get("/search/suggestions/{workspace_id}")
async def get_search_suggestions(
    workspace_id: str,
    query: str = Query(..., min_length=2),
    limit: int = Query(5, le=10),
    current_user: User = Depends(get_current_active_user)
):
    """Get search suggestions based on document content"""
    if not await verify_workspace_access(current_user, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Simple keyword-based suggestions from document titles and content
    from app.database import get_database
    from bson import ObjectId
    
    db = get_database()
    
    # Search in titles and descriptions
    pipeline = [
        {
            "$match": {
                "workspace_id": ObjectId(workspace_id),
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}},
                    {"tags": {"$regex": query, "$options": "i"}}
                ]
            }
        },
        {
            "$project": {
                "title": 1,
                "description": 1,
                "tags": 1
            }
        },
        {"$limit": limit}
    ]
    
    suggestions = []
    async for doc in db.documents.aggregate(pipeline):
        suggestions.append({
            "text": doc["title"],
            "type": "document",
            "document_id": str(doc["_id"])
        })
    
    return suggestions