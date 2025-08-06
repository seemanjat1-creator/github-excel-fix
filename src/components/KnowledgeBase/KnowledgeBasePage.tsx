import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentAPI } from '../../lib/api';
import { 
  Upload, FileText, Search, Filter, Trash2, Eye, Edit3, 
  Plus, BookOpen, BarChart3, Tag, Calendar, User, AlertCircle,
  Download, FileType, Clock, CheckCircle, XCircle, Shield
} from 'lucide-react';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { useAuth } from '../../contexts/AuthContext';
import { workspaceAPI } from '../../lib/api';
import { DocumentUploadModal } from './DocumentUploadModal';
import { DocumentViewModal } from './DocumentViewModal';
import { DocumentEditModal } from './DocumentEditModal';
import { SearchModal } from './SearchModal';
import { formatDate, formatTime } from '../../lib/utils';
import toast from 'react-hot-toast';

export const KnowledgeBasePage: React.FC = () => {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  
  const queryClient = useQueryClient();
  const { currentWorkspace, isCurrentUserAdmin } = useWorkspace();
  const { user } = useAuth();

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', currentWorkspace?.id, searchTerm, filterType, filterStatus],
    queryFn: () => documentAPI.getWorkspaceDocuments(
      currentWorkspace!.id,
      filterType !== 'all' ? filterType : undefined,
      filterStatus !== 'all' ? filterStatus : undefined,
      searchTerm || undefined
    ),
    enabled: !!currentWorkspace?.id,
  });

  const { data: documentStats } = useQuery({
    queryKey: ['document-stats', currentWorkspace?.id],
    queryFn: () => documentAPI.getDocumentStats(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => documentAPI.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', currentWorkspace?.id] });
      queryClient.invalidateQueries({ queryKey: ['document-stats', currentWorkspace?.id] });
      toast.success('Document deleted successfully');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Failed to delete document';
      toast.error(errorMessage);
    },
  });

  const handleViewDocument = (document: any) => {
    setSelectedDocument(document);
    setShowViewModal(true);
  };

  const handleEditDocument = (document: any) => {
    setSelectedDocument(document);
    setShowEditModal(true);
  };

  const handleDeleteDocument = (document: any) => {
    if (window.confirm(`Are you sure you want to delete "${document.title}"? This action cannot be undone.`)) {
      deleteMutation.mutate(document.id);
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

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

  const filteredDocuments = documents?.filter((doc: any) => {
    const matchesSearch = !searchTerm || 
      doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.file_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (doc.description && doc.description.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesType = filterType === 'all' || doc.document_type === filterType;
    const matchesStatus = filterStatus === 'all' || doc.status === filterStatus;
    
    return matchesSearch && matchesType && matchesStatus;
  }) || [];

  const isAdmin = isCurrentUserAdmin;

  // Show no workspace state
  if (!currentWorkspace) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <BookOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspace Selected</h3>
            <p className="text-gray-600">Please select a workspace to manage knowledge base</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-gray-600">Workspace: {currentWorkspace.name}</p>
          <p className="text-sm text-gray-500 mt-1">
            {documentStats?.total_documents || 0} documents • {documentStats?.total_chunks || 0} chunks
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSearchModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Search className="w-4 h-4" />
            Advanced Search
          </button>
          {isAdmin && (
            <button
              onClick={() => setShowUploadModal(true)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Upload Document
            </button>
          )}
        </div>
      </div>

      {!isAdmin && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-yellow-600" />
            <div>
              <h3 className="text-lg font-medium text-yellow-900 mb-2">Administrator Access Required</h3>
              <p className="text-yellow-800 mb-4">
                Only workspace administrators can upload and manage documents.
              </p>
              <div className="text-sm text-yellow-700">
                <p><strong>Current Role:</strong> {isAdmin ? 'Administrator' : 'Member'}</p>
                <p><strong>Required Role:</strong> Administrator</p>
                <p><strong>User ID:</strong> {user?.id}</p>
                <p><strong>Admin ID:</strong> {currentWorkspace?.admin_id}</p>
                <p className="mt-2">Contact your workspace administrator to request changes to these settings.</p>
                {user?.is_admin && (
                  <div className="mt-4">
                    <button
                      onClick={async () => {
                        try {
                          await workspaceAPI.makeAdminOfAllWorkspaces();
                          toast.success('You are now admin of all workspaces!');
                          window.location.reload();
                        } catch (error: any) {
                          console.error('Error making admin:', error);
                          const errorMessage = error.response?.data?.detail || 'Error making you admin';
                          toast.error(errorMessage);
                        }
                      }}
                      className="mt-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm"
                    >
                      Make Me Admin of All Workspaces
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Statistics Cards */}
      {documentStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Documents</p>
                <p className="text-2xl font-bold text-gray-900">{documentStats.total_documents}</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-100">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Size</p>
                <p className="text-2xl font-bold text-gray-900">
                  {(documentStats.total_size / (1024 * 1024)).toFixed(1)}MB
                </p>
              </div>
              <div className="p-3 rounded-lg bg-green-100">
                <BarChart3 className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">AI Chunks</p>
                <p className="text-2xl font-bold text-gray-900">{documentStats.total_chunks}</p>
              </div>
              <div className="p-3 rounded-lg bg-purple-100">
                <Search className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Access</p>
                <p className="text-2xl font-bold text-gray-900">{documentStats.avg_access_count}</p>
              </div>
              <div className="p-3 rounded-lg bg-orange-100">
                <Eye className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm border mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="all">All Types</option>
              <option value="pdf">PDF</option>
              <option value="docx">DOCX</option>
              <option value="txt">TXT</option>
              <option value="xlsx">XLSX</option>
              <option value="xls">XLS</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="all">All Status</option>
              <option value="ready">Ready</option>
              <option value="processing">Processing</option>
              <option value="error">Error</option>
            </select>
          </div>

          {(searchTerm || filterType !== 'all' || filterStatus !== 'all') && (
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterType('all');
                setFilterStatus('all');
              }}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-lg shadow-sm border">
        {isLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading documents...</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {documents?.length === 0 ? 'No documents uploaded' : 'No documents match your filters'}
            </h3>
            <p className="text-gray-600 mb-4">
              {documents?.length === 0 
                ? 'Upload your first document to build your AI knowledge base'
                : 'Try adjusting your search terms or filters'
              }
            </p>
            {isAdmin && documents?.length === 0 && (
              <button
                onClick={() => setShowUploadModal(true)}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 mx-auto"
              >
                <Plus className="w-4 h-4" />
                Upload First Document
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Document
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Chunks
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredDocuments.map((document: any) => (
                  <tr key={document._id ?? document.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="text-2xl">{getTypeIcon(document.document_type)}</div>
                        <div>
                          <p className="font-medium text-gray-900">{document.title}</p>
                          <p className="text-sm text-gray-600">{document.file_name}</p>
                          {document.description && (
                            <p className="text-xs text-gray-500 mt-1 truncate max-w-xs">
                              {document.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">
                        {document.document_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(document.status)}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(document.status)}`}>
                          {document.status}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {(document.file_size / 1024).toFixed(1)} KB
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {document.chunk_count}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {formatDate(document.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleViewDocument(document)}
                          className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                          title="View document"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {isAdmin && (
                          <>
                            <button
                              onClick={() => handleEditDocument(document)}
                              className="p-2 text-gray-400 hover:text-green-600 transition-colors"
                              title="Edit document"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteDocument(document)}
                              disabled={deleteMutation.isPending}
                              className="p-2 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                              title="Delete document"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* AI Integration Info */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          AI Knowledge Integration
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-blue-800">
          <div>
            <h4 className="font-medium mb-2">How it works:</h4>
            <ul className="text-sm space-y-1">
              <li>• Documents are automatically processed into searchable chunks</li>
              <li>• AI embeddings are generated for semantic search</li>
              <li>• Content is used to answer customer questions</li>
              <li>• Vector database enables intelligent document retrieval</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">Supported formats:</h4>
            <ul className="text-sm space-y-1">
              <li>• PDF documents (up to 10MB)</li>
              <li>• Word documents (.docx)</li>
              <li>• Plain text files (.txt)</li>
              <li>• Excel spreadsheets (.xlsx, .xls)</li>
              <li>• Automatic text extraction and chunking</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Modals */}
      <DocumentUploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        workspaceId={currentWorkspace.id}
      />

      {selectedDocument && (
        <>
          <DocumentViewModal
            isOpen={showViewModal}
            onClose={() => {
              setShowViewModal(false);
              setSelectedDocument(null);
            }}
            document={selectedDocument}
          />

          <DocumentEditModal
            isOpen={showEditModal}
            onClose={() => {
              setShowEditModal(false);
              setSelectedDocument(null);
            }}
            document={selectedDocument}
          />
        </>
      )}

      <SearchModal
        isOpen={showSearchModal}
        onClose={() => setShowSearchModal(false)}
        workspaceId={currentWorkspace.id}
      />
    </div>
  );
};