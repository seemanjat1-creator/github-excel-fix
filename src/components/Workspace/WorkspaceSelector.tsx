import React, { useState, useEffect } from 'react';
import { ChevronDown, Plus, Settings, Trash2, Building } from 'lucide-react';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { useAuth } from '../../contexts/AuthContext';
import { CreateWorkspaceModal } from './CreateWorkspaceModal';

export const WorkspaceSelector: React.FC = () => {
  const { workspaces, currentWorkspace, setCurrentWorkspace, deleteWorkspace } = useWorkspace();
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const handleWorkspaceSelect = (workspace: any) => {
    setCurrentWorkspace(workspace);
    setIsOpen(false);
  };

  const handleDeleteWorkspace = async (e: React.MouseEvent, workspaceId: string) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this workspace? This action cannot be undone.')) {
      try {
        await deleteWorkspace(workspaceId);
      } catch (error) {
        // Error is handled in context
      }
    }
  };

  const isAdmin = (workspace: any) => workspace.admin_id === user?.id;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest('.workspace-selector')) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  return (
    <>
      <div className="relative workspace-selector">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between p-3 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 text-left"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
              <Building className="w-4 h-4 text-white" />
            </div>
            <div className="text-left">
              <p className="text-sm font-medium text-white truncate">
                {currentWorkspace?.name || 'Select Workspace'}
              </p>
              <p className="text-xs text-slate-300">
                {currentWorkspace ? (isAdmin(currentWorkspace) ? 'Admin' : 'Member') : 'No workspace'}
              </p>
            </div>
          </div>
          <ChevronDown className={`w-4 h-4 text-slate-300 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-80 overflow-y-auto">
            <div className="p-2">
              <button
                onClick={() => {
                  setShowCreateModal(true);
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-3 p-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors focus:outline-none focus:bg-gray-100"
              >
                <Plus className="w-4 h-4 text-green-600" />
                <span className="text-sm">Create Workspace</span>
              </button>
            </div>

            {workspaces.length > 0 && (
              <>
                <div className="border-t border-gray-200" />
                <div className="p-2 space-y-1">
                  {workspaces.map((workspace, index) => (
                    <div
                      key={workspace.id || index}
                      className={`group flex items-center justify-between p-2 rounded-md cursor-pointer transition-colors text-left ${
                        currentWorkspace?.id === workspace.id
                          ? 'bg-green-50 text-green-900 border border-green-200'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                      onClick={() => handleWorkspaceSelect(workspace)}
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div
                          className={`w-6 h-6 rounded flex items-center justify-center ${
                            currentWorkspace?.id === workspace.id ? 'bg-green-500' : 'bg-gray-400'
                          }`}
                        >
                          <Building className="w-3 h-3 text-white" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{workspace.name}</p>
                          <p className="text-xs text-gray-500">
                            {isAdmin(workspace) ? 'Admin' : 'Member'}
                          </p>
                        </div>
                      </div>

                      {isAdmin(workspace) && workspaces.length > 1 && (
                        <button
                          onClick={(e) => handleDeleteWorkspace(e, workspace.id)}
                          className="p-1 text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity focus:outline-none focus:opacity-100"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      <CreateWorkspaceModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </>
  );
};
