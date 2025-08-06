"""
Utility functions for Excel file handling and data processing.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ExcelDataFormatter:
    """Helper class for formatting Excel data for better AI understanding"""
    
    @staticmethod
    def format_table_for_ai(
        headers: List[str], 
        rows: List[List[str]], 
        table_name: str = "Data Table"
    ) -> str:
        """
        Format tabular data in a way that's optimal for AI understanding.
        Creates natural language descriptions of table content.
        """
        if not headers or not rows:
            return ""
        
        formatted_parts = []
        formatted_parts.append(f"=== {table_name} ===")
        
        # Add table structure description
        formatted_parts.append(f"This table contains {len(rows)} rows and {len(headers)} columns.")
        formatted_parts.append(f"Columns: {', '.join(headers)}")
        formatted_parts.append("")
        
        # Format each row with natural language
        for row_idx, row in enumerate(rows, 1):
            if len(row) != len(headers):
                continue  # Skip malformed rows
            
            row_description = f"Row {row_idx}: "
            row_parts = []
            
            for header, value in zip(headers, row):
                if value and str(value).strip():
                    row_parts.append(f"{header} is {value}")
            
            if row_parts:
                row_description += ", ".join(row_parts)
                formatted_parts.append(row_description)
        
        return "\n".join(formatted_parts)
    
    @staticmethod
    def extract_key_value_pairs(content: str) -> Dict[str, str]:
        """
        Extract key-value pairs from Excel content for better searchability.
        """
        pairs = {}
        
        # Look for patterns like "Header: Value"
        pattern = r'([A-Za-z][A-Za-z0-9\s]+):\s*([^\|]+)'
        matches = re.findall(pattern, content)
        
        for key, value in matches:
            key = key.strip()
            value = value.strip()
            if key and value and len(key) < 50 and len(value) < 200:
                pairs[key] = value
        
        return pairs
    
    @staticmethod
    def detect_data_types(content: str) -> Dict[str, Any]:
        """
        Analyze Excel content to detect data types and patterns.
        """
        analysis = {
            "has_numerical_data": False,
            "has_dates": False,
            "has_formulas": False,
            "has_headers": False,
            "estimated_table_count": 0,
            "data_patterns": []
        }
        
        # Check for numerical data
        if re.search(r'\b\d+\.?\d*\b', content):
            analysis["has_numerical_data"] = True
        
        # Check for dates
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}'   # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, content):
                analysis["has_dates"] = True
                break
        
        # Check for formulas
        if "Formula:" in content or "=" in content:
            analysis["has_formulas"] = True
        
        # Check for headers
        if "Headers:" in content:
            analysis["has_headers"] = True
        
        # Count worksheets/tables
        worksheet_count = len(re.findall(r'WORKSHEET \d+:', content))
        analysis["estimated_table_count"] = worksheet_count
        
        return analysis

class ExcelSearchOptimizer:
    """Optimizer for Excel content search and retrieval"""
    
    @staticmethod
    def enhance_excel_query(query: str, content_analysis: Dict[str, Any]) -> str:
        """
        Enhance search query based on Excel content analysis.
        """
        enhanced_query = query
        
        # Add context based on content type
        if content_analysis.get("has_numerical_data"):
            enhanced_query += " numerical data values"
        
        if content_analysis.get("has_dates"):
            enhanced_query += " date information"
        
        if content_analysis.get("has_headers"):
            enhanced_query += " table headers columns"
        
        return enhanced_query
    
    @staticmethod
    def rank_excel_chunks(chunks: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Re-rank Excel chunks based on content relevance.
        """
        query_lower = query.lower()
        
        for chunk in chunks:
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            
            # Base relevance score
            relevance = 0.0
            
            # Boost for header matches
            if metadata.get("has_headers") and any(word in content.lower() for word in query_lower.split()):
                relevance += 0.3
            
            # Boost for worksheet name matches
            worksheet_info = metadata.get("worksheet_info", "")
            if any(word in worksheet_info.lower() for word in query_lower.split()):
                relevance += 0.2
            
            # Boost for structured data
            row_count = metadata.get("row_count", 0)
            if row_count > 3:
                relevance += 0.1
            
            chunk["excel_relevance"] = relevance
        
        # Sort by combined relevance
        return sorted(chunks, key=lambda x: x.get("excel_relevance", 0), reverse=True)

# Utility functions for Excel processing
def is_excel_file(filename: str) -> bool:
    """Check if file is an Excel file"""
    return filename.lower().endswith(('.xlsx', '.xls'))

def get_excel_file_info(filename: str, file_size: int) -> Dict[str, Any]:
    """Get basic info about Excel file"""
    return {
        "is_excel": is_excel_file(filename),
        "excel_type": "xlsx" if filename.lower().endswith('.xlsx') else "xls" if filename.lower().endswith('.xls') else None,
        "estimated_processing_time": max(5, file_size // (1024 * 1024) * 2),  # Rough estimate in seconds
        "requires_special_handling": True
    }

def validate_excel_upload(file_size: int, filename: str) -> Tuple[bool, str]:
    """Validate Excel file for upload"""
    if not is_excel_file(filename):
        return False, "File is not an Excel file"
    
    # Check file size (Excel files can be larger due to formatting)
    max_excel_size = 15 * 1024 * 1024  # 15MB for Excel files
    if file_size > max_excel_size:
        return False, f"Excel file too large. Maximum size is {max_excel_size // (1024*1024)}MB"
    
    return True, ""