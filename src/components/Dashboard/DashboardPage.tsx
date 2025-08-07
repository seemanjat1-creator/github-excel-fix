import React from 'react';
import { Plus, Users, MessageCircle, Phone, CheckCircle, Building } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { chatAPI, phoneAPI } from '../../lib/api';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { CreateWorkspaceModal } from '../Workspace/CreateWorkspaceModal';

export const DashboardPage: React.FC = () => {
  const { currentWorkspace, workspaces, isLoading: workspaceLoading, isCurrentUserAdmin } = useWorkspace();
  const [showCreateModal, setShowCreateModal] = React.useState(false);

  const { data: chats, isLoading: chatsLoading } = useQuery({
    queryKey: ['chats', currentWorkspace?.id],
    queryFn: () => chatAPI.getWorkspaceChats(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
    retry: 1,
    staleTime: 30000,
  });

  const { data: phones, isLoading: phonesLoading } = useQuery({
    queryKey: ['phones', currentWorkspace?.id],
    queryFn: () => phoneAPI.getWorkspacePhones(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
    retry: 1,
    staleTime: 30000,
  });

  const { data: qualifiedLeads, isLoading: leadsLoading } = useQuery({
    queryKey: ['qualified-leads', currentWorkspace?.id],
    queryFn: () => chatAPI.getQualifiedLeads(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
    retry: 1,
    staleTime: 30000,
  });

  if (workspaceLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading workspaces...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!currentWorkspace) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Building className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspace Selected</h3>
            <p className="text-gray-600 mb-4">Create or select a workspace to get started</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 mx-auto"
            >
              <Plus className="w-4 h-4" />
              Create Workspace
            </button>
          </div>
        </div>
        <CreateWorkspaceModal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
        />
      </div>
    );
  }

  const stats = [
    {
      name: 'Active Chats',
      value: chatsLoading ? '...' : (chats?.length || 0),
      icon: MessageCircle,
      color: 'bg-blue-500',
    },
    {
      name: 'Connected Phones',
      value: phonesLoading ? '...' : (phones?.filter((p: any) => p.status === 'connected').length || 0),
      icon: Phone,
      color: 'bg-green-500',
    },
    {
      name: 'Qualified Leads',
      value: leadsLoading ? '...' : (qualifiedLeads?.length || 0),
      icon: CheckCircle,
      color: 'bg-purple-500',
    },
    {
      name: 'Team Members',
      value: (currentWorkspace?.member_ids?.length || 0) + 1,
      icon: Users,
      color: 'bg-orange-500',
    },
  ];

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Workspace: {currentWorkspace.name}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-gray-500">Role:</span>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              isCurrentUserAdmin ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
            }`}>
              {isCurrentUserAdmin ? 'Administrator' : 'Member'}
            </span>
          </div>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Workspace
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Workspace</h2>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Building className="w-8 h-8 text-green-500" />
              <div>
                <h3 className="font-medium text-gray-900">{currentWorkspace.name}</h3>
                <p className="text-sm text-gray-600">{currentWorkspace.description || 'No description'}</p>
              </div>
            </div>
            <div className="pt-3 border-t border-gray-200">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Status:</span>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  currentWorkspace.status === 'active'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {currentWorkspace.status}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-gray-600">Members:</span>
                <span className="font-medium">{(currentWorkspace.member_ids?.length || 0) + 1}</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-gray-600">Created:</span>
                <span className="font-medium">{new Date(currentWorkspace.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Chats</h2>
          <div className="space-y-3">
            {chats?.slice(0, 5).map((chat: any) => (
              <div key={chat.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">{chat.customer_name || chat.customer_phone}</p>
                  <p className="text-sm text-gray-600">{chat.customer_phone}</p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  chat.status === 'qualified'
                    ? 'bg-green-100 text-green-800'
                    : chat.status === 'active'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {chat.status}
                </span>
              </div>
            ))}
            {(!chats || chats.length === 0) && (
              <div className="text-center py-8">
                <MessageCircle className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500">No chats yet</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">WhatsApp Numbers</h2>
          <div className="space-y-3">
            {phones?.map((phone: any) => (
              <div key={phone.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">{phone.phone_number}</p>
                  <p className="text-sm text-gray-600">{phone.display_name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    phone.status === 'connected'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {phone.status}
                  </span>
                </div>
              </div>
            ))}
            {(!phones || phones.length === 0) && (
              <div className="text-center py-8">
                <Phone className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500">No phone numbers</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <CreateWorkspaceModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </div>
  );
};
