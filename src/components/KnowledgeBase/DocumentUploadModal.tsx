import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Upload, FileText, AlertCircle, Tag, Plus, Trash2 } from 'lucide-react';
import { documentAPI } from '../../lib/api';
import toast from 'react-hot-toast';

const schema = yup.object({
  title: yup.string().optional(),
  description: yup.string().optional(),
});

type FormData = yup.InferType<typeof schema>;

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({ 
  isOpen, 
  onClose, 
  workspaceId 
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [dragActive, setDragActive] = useState(false);
  
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<FormData>({
    resolver: yupResolver(schema),
  });

  const title = watch('title');

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; title?: string; description?: string; tags: string[] }) =>
      documentAPI.uploadDocument(workspaceId, data.file, data.title, data.description, data.tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
      queryClient.invalidateQueries({ queryKey: ['document-stats', workspaceId] });
      toast.success('Document uploaded successfully');
      handleClose();
    },
    onError: (error: any) => {
      let errorMessage = 'Failed to upload document';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      toast.error(errorMessage);
    },
  });

  const onSubmit = (data: FormData) => {
    if (!selectedFile) {
      toast.error('Please select a file to upload');
      return;
    }

    console.log('Upload submission:', {
      file: selectedFile.name,
      size: selectedFile.size,
      type: selectedFile.type,
      workspaceId,
      title: data.title,
      tags: tags.length
    });

    uploadMutation.mutate({
      file: selectedFile,
      title: data.title || selectedFile.name,
      description: data.description,
      tags: tags,
    });
  };

  const handleClose = () => {
    reset();
    setSelectedFile(null);
    setTags([]);
    setNewTag('');
    onClose();
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (isValidFileType(file)) {
        setSelectedFile(file);
      } else {
        toast.error('Invalid file type. Only PDF, DOCX, and TXT files are allowed.');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (isValidFileType(file)) {
        setSelectedFile(file);
      } else {
        toast.error('Invalid file type. Only PDF, DOCX, and TXT files are allowed.');
      }
    }
  };

  const isValidFileType = (file: File) => {
    const validTypes = [
      'application/pdf', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
      'text/plain',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel'
    ];
    const validExtensions = ['.pdf', '.docx', '.txt', '.xlsx', '.xls'];
    
    console.log('File validation:', {
      fileName: file.name,
      fileType: file.type,
      fileSize: file.size
    });
    
    // Check file type and extension
    const hasValidType = validTypes.includes(file.type);
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    
    const isValid = hasValidType || hasValidExtension;
    console.log('File validation result:', { hasValidType, hasValidExtension, isValid });
    return isValid;
  };

  const addTag = () => {
    const trimmedTag = newTag.trim().toLowerCase();
    if (trimmedTag && trimmedTag.length >= 2 && !tags.map(t => t.toLowerCase()).includes(trimmedTag)) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    } else if (trimmedTag.length < 2) {
      toast.error('Tag must be at least 2 characters');
    } else if (tags.map(t => t.toLowerCase()).includes(trimmedTag)) {
      toast.error('Tag already exists');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const getFileIcon = (fileName: string) => {
    if (fileName.toLowerCase().endsWith('.pdf')) return '📄';
    if (fileName.toLowerCase().endsWith('.docx')) return '📝';
    if (fileName.toLowerCase().endsWith('.txt')) return '📋';
    if (fileName.toLowerCase().endsWith('.xlsx')) return '📊';
    if (fileName.toLowerCase().endsWith('.xls')) return '📊';
    return '📄';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
              <Upload className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Upload Document</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          {/* File Upload Area */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Document *
            </label>
            
            {!selectedFile ? (
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-green-500 bg-green-50' 
                    : 'border-gray-300 hover:border-green-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-900 mb-2">
                  Drop your document here, or click to browse
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  Supports PDF, DOCX, TXT, and Excel files up to 10MB
                </p>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.xlsx,.xls"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg cursor-pointer inline-flex items-center gap-2"
                >
                  <FileText className="w-4 h-4" />
                  Choose File
                </label>
              </div>
            ) : (
              <div className="border border-gray-300 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">{getFileIcon(selectedFile.name)}</div>
                    <div>
                      <p className="font-medium text-gray-900">{selectedFile.name}</p>
                      <p className="text-sm text-gray-600">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Document Details */}
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Document Title
              </label>
              <input
                {...register('title')}
                type="text"
                placeholder={selectedFile ? selectedFile.name : "Enter document title"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              {errors.title && (
                <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Leave empty to use filename as title
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                {...register('description')}
                rows={3}
                placeholder="Brief description of the document content..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
              )}
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags
            </label>
            
            {/* Existing Tags */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {tags.map((tag, index) => (
                  <span
                    key={index}
                    className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm flex items-center gap-2"
                  >
                    <Tag className="w-3 h-3" />
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="text-blue-500 hover:text-blue-700"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Add New Tag */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                placeholder="Add a tag..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              <button
                type="button"
                onClick={addTag}
                disabled={!newTag.trim()}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:bg-gray-300 flex items-center gap-1"
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Tags help organize and search documents
            </p>
          </div>

          {/* Processing Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-medium text-blue-900 mb-1">Document Processing</h4>
                <ul className="text-xs text-blue-800 space-y-1">
                  <li>• Text will be extracted and processed for AI search</li>
                  <li>• Document will be split into logical chunks for better retrieval</li>
                  <li>• Excel files: Each worksheet is processed separately with table structure preserved</li>
                  <li>• Vector embeddings will be generated for semantic search</li>
                  <li>• Processing may take a few moments for large documents</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors disabled:bg-gray-400 flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              {uploadMutation.isPending ? 'Uploading...' : 'Upload Document'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};