"""
Enhanced document service with improved Excel integration and error handling.
This extends the base document service with Excel-specific optimizations.
"""

import logging
from typing import List, Dict, Any, Optional
from app.services.document_service import DocumentService
from app.services.excel_processor import excel_processor
from app.models.document import DocumentType
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedDocumentService(DocumentService):
    """Enhanced document service with Excel support and optimizations"""
    
    def __init__(self):
        super().__init__()
        self.excel_chunk_size = 1000  # Larger chunks for Excel data
        self.excel_chunk_overlap = 150  # More overlap for table context
    
    async def _process_document_chunks(self, document_id: str, content: str, workspace_id: str):
        """Enhanced chunk processing with Excel-specific handling"""
        try:
            logger.info(f"Starting enhanced chunk processing for document {document_id}")
            db = self.get_database()
            
            # Get document to check type
            doc_data = await db.documents.find_one({"_id": ObjectId(document_id)})
            if not doc_data:
                raise ValueError(f"Document {document_id} not found")
            
            document_type = doc_data.get("document_type")
            
            # Use Excel-specific processing for Excel files
            if document_type in ["xlsx", "xls"]:
                await self._process_excel_chunks(document_id, content, workspace_id, doc_data)
            else:
                # Use parent class method for other file types
                await super()._process_document_chunks(document_id, content, workspace_id)
                
        except Exception as e:
            logger.error(f"Enhanced chunk processing error: {e}")
            raise
    
    async def _process_excel_chunks(
        self, 
        document_id: str, 
        content: str, 
        workspace_id: str, 
        doc_data: Dict[str, Any]
    ):
        """Process Excel content with specialized chunking"""
        try:
            logger.info(f"Processing Excel chunks for document {document_id}")
            db = self.get_database()
            
            # Get Excel metadata
            excel_metadata = excel_processor.get_excel_metadata("", doc_data["file_name"])
            
            # Create Excel-specific chunks
            chunk_data_list = excel_processor.create_excel_chunks(content, doc_data["file_name"])
            logger.info(f"Created {len(chunk_data_list)} Excel chunks")
            
            # Limit chunks to prevent excessive processing
            if len(chunk_data_list) > self.max_chunks_per_document:
                chunk_data_list = chunk_data_list[:self.max_chunks_per_document]
                logger.warning(f"Limited Excel chunks to {self.max_chunks_per_document}")
            
            # Generate embeddings for each chunk
            chunk_documents = []
            successful_chunks = 0
            
            for i, chunk_data in enumerate(chunk_data_list):
                chunk_content = chunk_data["content"]
                chunk_metadata = chunk_data["metadata"]
                
                if chunk_content.strip():
                    logger.info(f"Generating embedding for Excel chunk {i+1}/{len(chunk_data_list)}")
                    
                    # Use specialized prompt for Excel content
                    embedding_content = self._prepare_excel_content_for_embedding(chunk_content)
                    embedding = await openai_service.generate_embedding(embedding_content)
                    
                    if embedding:
                        # Enhanced metadata for Excel chunks
                        combined_metadata = {
                            "word_count": len(chunk_content.split()),
                            "char_count": len(chunk_content),
                            "chunk_type": "excel_data",
                            "document_type": doc_data["document_type"],
                            "excel_metadata": excel_metadata,
                            **chunk_metadata
                        }
                        
                        chunk_doc = {
                            "document_id": document_id,
                            "workspace_id": ObjectId(workspace_id),
                            "content": chunk_content,
                            "chunk_index": i,
                            "embedding": embedding,
                            "metadata": combined_metadata,
                            "created_at": datetime.utcnow()
                        }
                        chunk_documents.append(chunk_doc)
                        successful_chunks += 1
                    else:
                        logger.warning(f"Failed to generate embedding for Excel chunk {i}")
            
            # Insert chunks in batch
            if chunk_documents:
                await db.document_chunks.insert_many(chunk_documents)
                logger.info(f"Inserted {len(chunk_documents)} Excel chunks for document {document_id}")
            
            # Update document with chunk count and Excel metadata
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {
                    "chunk_count": len(chunk_documents),
                    "excel_metadata": excel_metadata,
                    "processing_stats": {
                        "total_chunks_created": len(chunk_data_list),
                        "successful_embeddings": successful_chunks,
                        "processing_method": "excel_specialized"
                    }
                }}
            )
            
        except Exception as e:
            logger.error(f"Excel chunk processing error: {e}")
            raise
    
    def _prepare_excel_content_for_embedding(self, content: str) -> str:
        """
        Prepare Excel content for better embedding generation.
        Adds context and structure information.
        """
        # Add context prefix for better embeddings
        if "WORKSHEET" in content:
            # This is worksheet content
            prepared_content = f"Excel spreadsheet data:\n{content}"
        else:
            # This is regular chunk content
            prepared_content = f"Tabular data from Excel file:\n{content}"
        
        # Ensure content isn't too long for embedding
        max_embedding_length = 8000
        if len(prepared_content) > max_embedding_length:
            prepared_content = prepared_content[:max_embedding_length]
        
        return prepared_content
    
    async def search_excel_content(
        self, 
        query: str, 
        workspace_id: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Specialized search for Excel content with table-aware ranking.
        """
        try:
            from app.models.document import DocumentSearch
            
            # Create search request specifically for Excel files
            search_request = DocumentSearch(
                query=query,
                workspace_id=workspace_id,
                limit=limit * 2,  # Get more results for filtering
                similarity_threshold=0.6,
                document_types=["xlsx", "xls"]
            )
            
            # Use parent search method
            results = await super().search_documents(search_request)
            
            # Re-rank results based on Excel-specific factors
            enhanced_results = []
            for result in results:
                # Calculate Excel-specific relevance score
                excel_score = self._calculate_excel_relevance(result, query)
                result.relevance_score = (result.relevance_score * 0.7) + (excel_score * 0.3)
                enhanced_results.append(result)
            
            # Sort by enhanced relevance and limit
            enhanced_results.sort(key=lambda x: x.relevance_score, reverse=True)
            return enhanced_results[:limit]
            
        except Exception as e:
            logger.error(f"Excel search error: {e}")
            return []
    
    def _calculate_excel_relevance(self, result: Any, query: str) -> float:
        """Calculate Excel-specific relevance score"""
        score = 0.0
        query_lower = query.lower()
        
        # Check if query matches worksheet names
        for chunk in result.chunks:
            metadata = chunk.get("metadata", {})
            worksheet_info = metadata.get("worksheet_info", "")
            
            if query_lower in worksheet_info.lower():
                score += 0.3
            
            # Boost score for chunks with headers
            if metadata.get("has_headers", False):
                score += 0.2
            
            # Boost score for chunks with more structured data
            row_count = metadata.get("row_count", 0)
            if row_count > 5:
                score += 0.1
        
        return min(score, 1.0)

# Create enhanced service instance
enhanced_document_service = EnhancedDocumentService()