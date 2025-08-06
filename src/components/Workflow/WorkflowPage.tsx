import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowAPI } from '../../lib/api';
import { Plus, Trash2, Edit3, GripVertical, GitBranch, Save, X, AlertCircle, Shield } from 'lucide-react';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { useAuth } from '../../contexts/AuthContext';
import { workspaceAPI } from '../../lib/api';
import { AddWorkflowStepModal } from './AddWorkflowStepModal';
import { EditWorkflowStepModal } from './EditWorkflowStepModal';
import toast from 'react-hot-toast';

export const WorkflowPage: React.FC = () => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingStep, setEditingStep] = useState<any>(null);
  const [draggedStep, setDraggedStep] = useState<any>(null);
  const queryClient = useQueryClient();
  const { currentWorkspace, isCurrentUserAdmin } = useWorkspace();
  const { user } = useAuth();

  const { data: workflowSteps, isLoading } = useQuery({
    queryKey: ['workflow-steps', currentWorkspace?.id],
    queryFn: () => workflowAPI.getWorkspaceSteps(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });

  const deleteStepMutation = useMutation({
    mutationFn: (stepId: string) => workflowAPI.deleteStep(stepId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-steps', currentWorkspace?.id] });
      toast.success('Workflow step deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete workflow step');
    },
  });

  const reorderStepsMutation = useMutation({
    mutationFn: (stepOrders: any[]) => workflowAPI.reorderSteps(currentWorkspace!.id, stepOrders),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-steps', currentWorkspace?.id] });
      toast.success('Workflow steps reordered successfully');
    },
    onError: () => {
      toast.error('Failed to reorder workflow steps');
    },
  });

  const handleDeleteStep = (step: any) => {
    if (window.confirm(`Are you sure you want to delete "${step.title}"? This action cannot be undone.`)) {
      deleteStepMutation.mutate(step.id);
    }
  };

  const handleDragStart = (e: React.DragEvent, step: any) => {
    setDraggedStep(step);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, targetStep: any) => {
    e.preventDefault();
    
    if (!draggedStep || draggedStep.id === targetStep.id) {
      setDraggedStep(null);
      return;
    }

    const steps = [...(workflowSteps || [])];
    const draggedIndex = steps.findIndex(s => s.id === draggedStep.id);
    const targetIndex = steps.findIndex(s => s.id === targetStep.id);

    // Remove dragged step and insert at target position
    const [removed] = steps.splice(draggedIndex, 1);
    steps.splice(targetIndex, 0, removed);

    // Create reorder data
    const stepOrders = steps.map((step, index) => ({
      step_id: step.id,
      step_number: index + 1
    }));

    reorderStepsMutation.mutate(stepOrders);
    setDraggedStep(null);
  };

  const getStepTypeColor = (type: string) => {
    switch (type) {
      case 'question':
        return 'bg-blue-100 text-blue-800';
      case 'information':
        return 'bg-green-100 text-green-800';
      case 'condition':
        return 'bg-yellow-100 text-yellow-800';
      case 'action':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const isAdmin = isCurrentUserAdmin;

  // Show no workspace state
  if (!currentWorkspace) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <GitBranch className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspace Selected</h3>
            <p className="text-gray-800">Please select a workspace to manage workflows</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Chat Workflow</h1>
          <p className="text-gray-800">Workspace: {currentWorkspace.name}</p>
          <p className="text-sm text-gray-700 mt-1">
            Define steps to guide AI conversations and qualify leads
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Step
          </button>
        )}
      </div>

      {!isAdmin && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-yellow-600" />
            <div>
              <h3 className="text-lg font-medium text-yellow-900 mb-2">Administrator Access Required</h3>
              <p className="text-yellow-800 mb-4">
                Only workspace administrators can manage workflow steps.
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

      {/* Workflow Steps */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto"></div>
            <p className="mt-2 text-gray-800">Loading workflow steps...</p>
          </div>
        ) : workflowSteps?.length === 0 ? (
          <div className="text-center py-12">
            <GitBranch className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No workflow steps defined</h3>
            <p className="text-gray-800 mb-4">
              Create your first workflow step to guide AI conversations
            </p>
            {isAdmin && (
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 mx-auto"
              >
                <Plus className="w-4 h-4" />
                Add First Step
              </button>
            )}
          </div>
        ) : (
          workflowSteps?.map((step: any) => (
            <div
              key={step.id}
              draggable={isAdmin}
              onDragStart={(e) => handleDragStart(e, step)}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, step)}
              className={`bg-white p-6 rounded-lg shadow-sm border hover:shadow-md transition-shadow ${
                isAdmin ? 'cursor-move' : ''
              } ${draggedStep?.id === step.id ? 'opacity-50' : ''}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  {isAdmin && (
                    <div className="mt-2">
                      <GripVertical className="w-5 h-5 text-gray-400" />
                    </div>
                  )}
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white font-semibold">
                        {step.step_number}
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900">{step.title}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStepTypeColor(step.step_type)}`}>
                        {step.step_type}
                      </span>
                      {step.is_required && (
                        <span className="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">
                          Required
                        </span>
                      )}
                    </div>
                    
                    <p className="text-gray-900 mb-4">{step.description}</p>
                    
                    {step.keywords && step.keywords.length > 0 && (
                      <div className="mb-3">
                        <p className="text-sm font-medium text-gray-800 mb-2">Keywords:</p>
                        <div className="flex flex-wrap gap-2">
                          {step.keywords.map((keyword: string, index: number) => (
                            <span
                              key={`keyword-${step.id}-${index}`}
                              className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-medium"
                            >
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {step.expected_response_pattern && (
                      <div className="mb-3">
                        <p className="text-sm font-medium text-gray-800 mb-1">Expected Response Pattern:</p>
                        <p className="text-sm text-gray-900 bg-gray-100 p-2 rounded font-medium">
                          {step.expected_response_pattern}
                        </p>
                      </div>
                    )}
                    
                    {step.follow_up_questions && step.follow_up_questions.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-gray-800 mb-2">Follow-up Questions:</p>
                        <ul className="text-sm text-gray-900 space-y-1">
                          {step.follow_up_questions.map((question: string, index: number) => (
                            <li key={`followup-${step.id}-${index}`} className="flex items-start gap-2">
                              <span className="text-gray-600 mt-1 font-bold">•</span>
                              <span>{question}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
                
                {isAdmin && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setEditingStep(step)}
                      className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                      title="Edit step"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteStep(step)}
                      className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                      title="Delete step"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Workflow Info */}
      {workflowSteps && workflowSteps.length > 0 && (
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">How Workflow Works</h3>
          <div className="space-y-2 text-blue-800">
            <p>• AI will guide customers through these steps in order</p>
            <p>• Required steps must be completed for lead qualification</p>
            <p>• AI uses keywords and patterns to detect step completion</p>
            <p>• Customers are moved to "Qualified Leads" when workflow is complete</p>
            <p>• If AI confidence is low, chats are moved to "Needs Human Help"</p>
          </div>
        </div>
      )}

      <AddWorkflowStepModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        workspaceId={currentWorkspace.id}
      />

      {editingStep && (
        <EditWorkflowStepModal
          isOpen={!!editingStep}
          onClose={() => setEditingStep(null)}
          step={editingStep}
        />
      )}
    </div>
  );
};