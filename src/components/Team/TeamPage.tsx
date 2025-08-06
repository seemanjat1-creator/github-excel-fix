import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceAPI, userAPI } from '../../lib/api';
import { Users, Plus, Trash2, Crown, Mail, Calendar, Shield, UserCheck } from 'lucide-react';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { useAuth } from '../../contexts/AuthContext';
import { AddMemberModal } from './AddMemberModal';
import { formatDate } from '../../lib/utils';
import toast from 'react-hot-toast';

export const TeamPage: React.FC = () => {
  const [showAddModal, setShowAddModal] = useState(false);
  const queryClient = useQueryClient();
  const { currentWorkspace, isCurrentUserAdmin } = useWorkspace();
  const { user } = useAuth();

  const { data: workspaceDetails, isLoading } = useQuery({
    queryKey: ['workspace-details', currentWorkspace?.id],
    queryFn: () => workspaceAPI.getById(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });

  const { data: teamMembers } = useQuery({
    queryKey: ['team-members', currentWorkspace?.id],
    queryFn: () => workspaceAPI.getTeamMembers(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) => 
      workspaceAPI.removeMember(currentWorkspace!.id, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members', currentWorkspace?.id] });
      queryClient.invalidateQueries({ queryKey: ['workspace-details', currentWorkspace?.id] });
      toast.success('Member removed successfully');
    },
    onError: () => {
      toast.error('Failed to remove member');
    },
  });

  const handleRemoveMember = (member: any) => {
    if (window.confirm(`Are you sure you want to remove ${member.full_name} from this workspace?`)) {
      removeMemberMutation.mutate(member.id);
    }
  };

  const isAdmin = isCurrentUserAdmin;
  const totalMembers = (teamMembers?.length || 0) + 1; // +1 for admin

  // Show no workspace state
  if (!currentWorkspace) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspace Selected</h3>
            <p className="text-gray-600">Please select a workspace to view team members</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Team Members</h1>
          <p className="text-gray-600">Workspace: {currentWorkspace.name}</p>
          <p className="text-sm text-gray-500 mt-1">
            {totalMembers} member{totalMembers !== 1 ? 's' : ''} total
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Member
          </button>
        )}
      </div>

      {!isAdmin && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-600" />
            <p className="text-blue-800">
              You can view all team members. Only workspace administrators can add or remove members.
            </p>
          </div>
        </div>
      )}

      {/* Workspace Admin Section */}
      <div className="bg-white rounded-lg shadow-sm border mb-6">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Crown className="w-5 h-5 text-yellow-500" />
              Workspace Administrator
            </h2>
          </div>
          
          {workspaceDetails && (
            <div className="flex items-center gap-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <div className="w-12 h-12 bg-yellow-500 rounded-full flex items-center justify-center">
                <span className="text-white font-semibold text-lg">
                  {workspaceDetails.admin?.full_name?.charAt(0).toUpperCase() || 'A'}
                </span>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-900">
                    {workspaceDetails.admin?.full_name || 'Administrator'}
                  </h3>
                  <Crown className="w-4 h-4 text-yellow-500" />
                </div>
                <p className="text-sm text-gray-600 flex items-center gap-1">
                  <Mail className="w-3 h-3" />
                  {workspaceDetails.admin?.email}
                </p>
                <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                  <Calendar className="w-3 h-3" />
                  Admin since {formatDate(workspaceDetails.created_at)}
                </p>
              </div>
              <div className="text-right">
                <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-medium">
                  Administrator
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Team Members Section */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-500" />
              Team Members
              {teamMembers && teamMembers.length > 0 && (
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm">
                  {teamMembers.length}
                </span>
              )}
            </h2>
          </div>

          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading team members...</p>
            </div>
          ) : teamMembers && teamMembers.length > 0 ? (
            <div className="space-y-4">
              {teamMembers.map((member: any) => (
                <div key={member.id} className="flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-white font-semibold text-lg">
                      {member.full_name?.charAt(0).toUpperCase() || member.email?.charAt(0).toUpperCase() || 'M'}
                    </span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900">{member.full_name}</h3>
                      <UserCheck className="w-4 h-4 text-green-500" />
                    </div>
                    <p className="text-sm text-gray-600 flex items-center gap-1">
                      <Mail className="w-3 h-3" />
                      {member.email}
                    </p>
                    <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                      <Calendar className="w-3 h-3" />
                      Joined {formatDate(member.joined_at || member.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                      Member
                    </span>
                    {isAdmin && (
                      <button
                        onClick={() => handleRemoveMember(member)}
                        disabled={removeMemberMutation.isPending}
                        className="p-2 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                        title="Remove member"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No team members yet</h3>
              <p className="text-gray-600 mb-4">
                {isAdmin 
                  ? "Add team members to collaborate on this workspace" 
                  : "No additional team members have been added to this workspace"
                }
              </p>
              {isAdmin && (
                <button
                  onClick={() => setShowAddModal(true)}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                  Add First Member
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Team Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Members</p>
              <p className="text-2xl font-bold text-gray-900">{totalMembers}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <Crown className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Administrators</p>
              <p className="text-2xl font-bold text-gray-900">1</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <UserCheck className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Active Members</p>
              <p className="text-2xl font-bold text-gray-900">
                {teamMembers?.filter((m: any) => m.is_active).length || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      <AddMemberModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        workspaceId={currentWorkspace.id}
      />
    </div>
  );
};