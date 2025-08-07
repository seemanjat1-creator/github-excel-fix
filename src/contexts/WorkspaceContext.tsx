import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { workspaceAPI } from '../lib/api';
import { useAuth } from './AuthContext';
import toast from 'react-hot-toast';

interface Workspace {
  id: string;
  name: string;
  description?: string;
  status: string;
  admin_id: string;
  member_ids: string[];
  created_at: string;
  updated_at: string;
  prompt_settings?: any;
  workflow_steps?: any[];
}

interface WorkspaceContextType {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isLoading: boolean;
  isCurrentUserAdmin: boolean;
  setCurrentWorkspace: (workspace: Workspace | null) => void;
  createWorkspace: (data: { name: string; description?: string }) => Promise<void>;
  refreshWorkspaces: () => Promise<void>;
  deleteWorkspace: (workspaceId: string) => Promise<void>;
  checkAdminAccess: (workspaceId?: string) => boolean;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};

interface WorkspaceProviderProps {
  children: ReactNode;
}

export const WorkspaceProvider: React.FC<WorkspaceProviderProps> = ({ children }) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { user, isAuthenticated } = useAuth();

  // Check if current user is admin of current workspace
  const isCurrentUserAdmin = React.useMemo(() => {
    if (!currentWorkspace || !user) return false;
    // Check if user is global admin OR workspace admin
    const isGlobalAdmin = user.is_admin === true;
    const isWorkspaceAdmin = currentWorkspace.admin_id === user.id;
    const isAdmin = isGlobalAdmin || isWorkspaceAdmin;
    console.log('Admin check:', { 
      currentWorkspace: currentWorkspace.id, 
      adminId: currentWorkspace.admin_id, 
      userId: user.id, 
      isGlobalAdmin,
      isWorkspaceAdmin,
      isAdmin
    });
    return isAdmin;
  }, [currentWorkspace, user]);

  const checkAdminAccess = (workspaceId?: string) => {
    if (!user) return false;
    
    // Global admins have access to all workspaces
    if (user.is_admin === true) {
      console.log('Global admin access granted for user:', user.id);
      return true;
    }
    
    const workspace = workspaceId 
      ? workspaces.find(w => w.id === workspaceId)
      : currentWorkspace;
    const isAdmin = workspace ? workspace.admin_id === user.id : false;
    console.log('Check admin access:', { workspaceId, userId: user.id, isAdmin });
    return isAdmin;
  };
  const refreshWorkspaces = async () => {
    if (!isAuthenticated || !user) return;
    
    try {
      setIsLoading(true);
      const data = await workspaceAPI.getAll();
      setWorkspaces(data);
      
      // Auto-select first workspace if none selected
      if (data.length > 0 && !currentWorkspace) {
        const savedWorkspaceId = localStorage.getItem('currentWorkspaceId');
        const savedWorkspace = savedWorkspaceId ? data.find(w => w.id === savedWorkspaceId) : null;
        setCurrentWorkspace(savedWorkspace || data[0]);
        if (savedWorkspace || data[0]) {
          localStorage.setItem('currentWorkspaceId', (savedWorkspace || data[0]).id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
      // Only show error if user is authenticated
      if (isAuthenticated) {
        toast.error('Failed to load workspaces');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const createWorkspace = async (data: { name: string; description?: string }) => {
    try {
      if (!user) {
        throw new Error('User not authenticated');
      }
      
      // Validate input
      if (!data.name || data.name.trim().length < 2) {
        throw new Error('Workspace name must be at least 2 characters');
      }
      
      const newWorkspace = await workspaceAPI.create(data);
      setWorkspaces(prev => [...prev, newWorkspace]);
      setCurrentWorkspace(newWorkspace);
      localStorage.setItem('currentWorkspaceId', newWorkspace.id);
    } catch (error) {
      console.error('Failed to create workspace:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to create workspace';
      throw error;
    }
  };

  const deleteWorkspace = async (workspaceId: string) => {
    try {
      if (!user) {
        throw new Error('User not authenticated');
      }
      await workspaceAPI.delete(workspaceId);
      setWorkspaces(prev => prev.filter(w => w.id !== workspaceId));
      
      // If deleted workspace was current, select another one
      if (currentWorkspace?.id === workspaceId) {
        const remaining = workspaces.filter(w => w.id !== workspaceId);
        const newCurrent = remaining.length > 0 ? remaining[0] : null;
        setCurrentWorkspace(newCurrent);
        if (newCurrent) {
          localStorage.setItem('currentWorkspaceId', newCurrent.id);
        } else {
          localStorage.removeItem('currentWorkspaceId');
        }
      }
      
      toast.success('Workspace deleted successfully');
    } catch (error) {
      console.error('Failed to delete workspace:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to delete workspace';
      toast.error(errorMessage);
      throw error;
    }
  };

  const handleSetCurrentWorkspace = (workspace: Workspace | null) => {
    setCurrentWorkspace(workspace);
    if (workspace) {
      localStorage.setItem('currentWorkspaceId', workspace.id);
    } else {
      localStorage.removeItem('currentWorkspaceId');
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      refreshWorkspaces();
    } else {
      setWorkspaces([]);
      setCurrentWorkspace(null);
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const value: WorkspaceContextType = {
    workspaces,
    currentWorkspace,
    isLoading,
    isCurrentUserAdmin,
    setCurrentWorkspace: handleSetCurrentWorkspace,
    createWorkspace,
    refreshWorkspaces,
    deleteWorkspace,
    checkAdminAccess,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
};