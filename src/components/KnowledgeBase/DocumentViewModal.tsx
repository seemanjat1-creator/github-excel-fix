import React from 'react';
import { X, FileText, Calendar, User, Tag, BarChart3, Eye, Download } from 'lucide-react';
import { formatDate, formatTime } from '../../lib/utils';

interface DocumentViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: any;
}

export const DocumentViewModal: React.FC<DocumentViewModalProps> = ({ 
  isOpen, 
  onClose, 
  document 
}) => {
  if (!isOpen || !document) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return '📄';
      case 'docx':
        return '📝';
      case 'txt':
        return '📋';
      case 'xlsx':
        return '📊';
      case 'xls':
        return '📊';
      default:
        return '📄';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="text-2xl">{getTypeIcon(document.document_type)}</div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{document.title}</h2>
              <p className="text-sm text-gray-600">{document.file_name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {/* Document Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Document Details</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Status:</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(document.status)}`}>
                      {document.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Type:</span>
                    <span className="text-sm font-medium">{document.document_type.toUpperCase()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Size:</span>
                    <span className="text-sm font-medium">{(document.file_size / 1024).toFixed(1)} KB</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Chunks:</span>
                    <span className="text-sm font-medium">{document.chunk_count}</span>
                  </div>
                </div>
              </div>

              {document.tags && document.tags.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {document.tags.map((tag: string, index: number) => (
                      <span
                        key={index}
                        className="bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs flex items-center gap-1"
                      >
                        <Tag className="w-3 h-3" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Usage Statistics</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Access Count:</span>
                    <span className="text-sm font-medium flex items-center gap-1">
                      <Eye className="w-3 h-3" />
                      {document.access_count} times
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Created:</span>
                    <span className="text-sm font-medium flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(document.created_at)}
                    </span>
                  </div>
                  {document.last_accessed && (
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Last Accessed:</span>
                      <span className="text-sm font-medium">
                        {formatDate(document.last_accessed)}
                      </span>
                    </div>
                  )}
                  {document.processed_at && (
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Processed:</span>
                      <span className="text-sm font-medium">
                        {formatDate(document.processed_at)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Description */}
          {document.description && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
              <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                {document.description}
              </p>
            </div>
          )}

          {/* Content Preview */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Content Preview</h3>
            <div className="bg-gray-50 border rounded-lg p-4 max-h-96 overflow-y-auto">
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                {document.content ? document.content.substring(0, 2000) : 'Content not available'}
                {document.content && document.content.length > 2000 && (
                  <span className="text-gray-500">... (truncated)</span>
                )}
              </pre>
            </div>
          </div>

          {/* AI Processing Info */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              AI Processing Information
            </h4>
            <div className="text-xs text-blue-800 space-y-1">
              <p>• This document has been processed into {document.chunk_count} searchable chunks</p>
              <p>• Vector embeddings have been generated for semantic search</p>
              <p>• AI chatbot can reference this content when answering questions</p>
              <p>• Content is automatically included in relevant conversations</p>
            </div>
          </div>
        </div>

        <div className="px-6 pb-6">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};