import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, Search, FileText, Tag, Clock, BarChart3 } from 'lucide-react';
import { documentAPI } from '../../lib/api';
import { formatDate } from '../../lib/utils';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
}

export const SearchModal: React.FC<SearchModalProps> = ({ 
  isOpen, 
  onClose, 
  workspaceId 
}) => {
  const [query, setQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.7);
  const [limit, setLimit] = useState(5);
  const [hasSearched, setHasSearched] = useState(false);

  const { data: searchResults, isLoading, refetch } = useQuery({
    queryKey: ['document-search', workspaceId, query, selectedTypes, selectedTags, similarityThreshold, limit],
    queryFn: () => documentAPI.searchDocuments({
      query,
      workspace_id: workspaceId,
      limit,
      similarity_threshold: similarityThreshold,
      document_types: selectedTypes.length > 0 ? selectedTypes : undefined,
      tags: selectedTags.length > 0 ? selectedTags : undefined,
    }),
    enabled: false, // Manual trigger
  });

  const handleSearch = () => {
    if (query.trim()) {
      setHasSearched(true);
      refetch();
    }
  };

  const toggleType = (type: string) => {
    setSelectedTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
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

  const getSimilarityColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600';
    if (score >= 0.8) return 'text-blue-600';
    if (score >= 0.7) return 'text-yellow-600';
    return 'text-gray-600';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <Search className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Advanced Document Search</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {/* Search Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Query
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Enter your search query..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSearch}
                disabled={!query.trim() || isLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg disabled:bg-gray-400 flex items-center gap-2"
              >
                <Search className="w-4 h-4" />
                {isLoading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Document Types */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Document Types
              </label>
              <div className="flex gap-2">
                {['pdf', 'docx', 'txt', 'xlsx', 'xls'].map((type) => (
                  <button
                    key={type}
                    onClick={() => toggleType(type)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedTypes.includes(type)
                        ? 'bg-blue-100 text-blue-800 border border-blue-300'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {getTypeIcon(type)} {type.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Search Parameters */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Similarity Threshold: {similarityThreshold}
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1"
                  step="0.05"
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Less strict</span>
                  <span>More strict</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Results
                </label>
                <select
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={5}>5 results</option>
                  <option value={10}>10 results</option>
                  <option value={15}>15 results</option>
                  <option value={20}>20 results</option>
                </select>
              </div>
            </div>
          </div>

          {/* Search Results */}
          {hasSearched && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Search Results
                {searchResults && (
                  <span className="text-sm font-normal text-gray-600 ml-2">
                    ({searchResults.length} found)
                  </span>
                )}
              </h3>

              {isLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                  <p className="mt-2 text-gray-600">Searching documents...</p>
                </div>
              ) : searchResults?.length === 0 ? (
                <div className="text-center py-8">
                  <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <h4 className="text-lg font-medium text-gray-900 mb-2">No results found</h4>
                  <p className="text-gray-600">
                    Try adjusting your search query or reducing the similarity threshold
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {searchResults?.map((result: any, index: number) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                      {/* Document Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="text-xl">{getTypeIcon(result.document.document_type)}</div>
                          <div>
                            <h4 className="font-medium text-gray-900">{result.document.title}</h4>
                            <p className="text-sm text-gray-600">{result.document.file_name}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-medium ${getSimilarityColor(result.similarity_score)}`}>
                            {(result.similarity_score * 100).toFixed(1)}% match
                          </div>
                          <div className="text-xs text-gray-500">
                            Relevance: {(result.relevance_score * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>

                      {/* Document Info */}
                      <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          {result.document.document_type.toUpperCase()}
                        </span>
                        <span className="flex items-center gap-1">
                          <BarChart3 className="w-3 h-3" />
                          {result.chunks.length} relevant chunks
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(result.document.created_at)}
                        </span>
                      </div>

                      {/* Tags */}
                      {result.document.tags && result.document.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3">
                          {result.document.tags.slice(0, 3).map((tag: string, tagIndex: number) => (
                            <span
                              key={tagIndex}
                              className="bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs flex items-center gap-1"
                            >
                              <Tag className="w-3 h-3" />
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Relevant Chunks */}
                      <div>
                        <h5 className="text-sm font-medium text-gray-700 mb-2">Relevant Content:</h5>
                        <div className="space-y-2">
                          {result.chunks.map((chunk: any, chunkIndex: number) => (
                            <div key={chunkIndex} className="bg-gray-50 p-3 rounded text-sm">
                              <p className="text-gray-700">
                                {chunk.content.length > 200 
                                  ? `${chunk.content.substring(0, 200)}...` 
                                  : chunk.content
                                }
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Search Tips */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Search Tips</h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• Use specific keywords for better results</li>
              <li>• Lower similarity threshold finds more results but may be less relevant</li>
              <li>• Higher similarity threshold finds fewer but more precise results</li>
              <li>• Search uses AI semantic understanding, not just keyword matching</li>
            </ul>
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