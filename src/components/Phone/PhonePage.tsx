import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { phoneAPI } from '../../lib/api';
import { Plus, Phone, Trash2, QrCode, CheckCircle, XCircle, Clock, AlertCircle, Shield } from 'lucide-react';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { useAuth } from '../../contexts/AuthContext';
import { workspaceAPI } from '../../lib/api';
import { AddPhoneModal } from './AddPhoneModal';
import { QRCodeModal } from './QRCodeModal';
import { DeletePhoneModal } from './DeletePhoneModal';
import toast from 'react-hot-toast';

export const PhonePage: React.FC = () => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [showQRModal, setShowQRModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedPhone, setSelectedPhone] = useState<any>(null);
  const queryClient = useQueryClient();
  const { currentWorkspace, isCurrentUserAdmin } = useWorkspace();
  const { user } = useAuth();

  const { data: phones, isLoading } = useQuery({
    queryKey: ['phones', currentWorkspace?.id],
    queryFn: () => phoneAPI.getWorkspacePhones(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });

  const connectMutation = useMutation({
    mutationFn: (phoneId: string) => phoneAPI.connectPhone(phoneId),
    onSuccess: (data, phoneId) => {
      const phone = phones?.find((p: any) => p.id === phoneId);
      if (phone && data.qr_code) {
        setSelectedPhone({ ...phone, qr_code: data.qr_code });
        setShowQRModal(true);
      }
      queryClient.invalidateQueries({ queryKey: ['phones', currentWorkspace?.id] });
      toast.success('QR code generated successfully');
    },
    onError: () => {
      toast.error('Failed to generate QR code');
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: (phoneId: string) => phoneAPI.disconnectPhone(phoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['phones', currentWorkspace?.id] });
      toast.success('Phone disconnected successfully');
    },
    onError: () => {
      toast.error('Failed to disconnect phone');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (phoneId: string) => phoneAPI.deletePhone(phoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['phones', currentWorkspace?.id] });
      toast.success('Phone number deleted successfully from workspace');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Failed to delete phone number';
      toast.error(errorMessage);
    },
  });

  const handleConnect = (phone: any) => {
    connectMutation.mutate(phone.id);
  };

  const handleDisconnect = (phone: any) => {
    if (window.confirm('Are you sure you want to disconnect this phone number?')) {
      disconnectMutation.mutate(phone.id);
    }
  };

  const handleDelete = (phone: any) => {
    setSelectedPhone(phone);
    setShowDeleteModal(true);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'connecting':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <XCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'bg-green-100 text-green-800';
      case 'connecting':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const isAdmin = isCurrentUserAdmin;
  const canAddMore = (phones?.length || 0) < 2;

  // Debug admin status
  React.useEffect(() => {
    console.log('PhonePage - Admin status:', {
      isAdmin,
      currentWorkspace: currentWorkspace?.id,
      user: user?.id,
      adminId: currentWorkspace?.admin_id
    });
  }, [isAdmin, currentWorkspace, user]);

  // Show no workspace state
  if (!currentWorkspace) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Phone className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspace Selected</h3>
            <p className="text-gray-600">Please select a workspace to manage phone numbers</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Phone Numbers</h1>
          <p className="text-gray-600">Workspace: {currentWorkspace.name}</p>
          <p className="text-sm text-gray-500 mt-1">
            {phones?.length || 0}/2 phone numbers added
          </p>
        </div>
        {isAdmin && canAddMore && (
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Phone Number
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
                Only workspace administrators can manage phone numbers.
              </p>
              <div className="text-sm text-yellow-700">
                <p><strong>Current Role:</strong> {isAdmin ? 'Administrator' : 'Member'}</p>
                <p><strong>Required Role:</strong> Administrator</p>
                <p><strong>User ID:</strong> {user?.id}</p>
                <p><strong>Admin ID:</strong> {currentWorkspace?.admin_id}</p>
                <p><strong>Is Global Admin:</strong> {user?.is_admin ? 'Yes' : 'No'}</p>
                <p className="mt-2">Contact your workspace administrator to request changes to these settings.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {!canAddMore && isAdmin && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-blue-600" />
            <p className="text-blue-800">
              Maximum of 2 phone numbers allowed per workspace. Delete a number to add a new one.
            </p>
          </div>
        </div>
      )}

      {/* Phone Numbers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-full text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading phone numbers...</p>
          </div>
        ) : phones?.length === 0 ? (
          <div className="col-span-full text-center py-8">
            <Phone className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No phone numbers added</h3>
            <p className="text-gray-600 mb-4">Add your first WhatsApp number to get started</p>
            {isAdmin && (
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 mx-auto"
              >
                <Plus className="w-4 h-4" />
                Add Phone Number
              </button>
            )}
          </div>
        ) : (
          phones?.map((phone: any) => (
            <div key={phone.id} className="bg-white p-6 rounded-lg shadow-sm border hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <Phone className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{phone.phone_number}</h3>
                    <p className="text-sm text-gray-600">{phone.display_name || 'No display name'}</p>
                  </div>
                </div>
                {isAdmin && (
                  <button
                    onClick={() => handleDelete(phone)}
                    className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Status:</span>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(phone.status)}
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(phone.status)}`}>
                      {phone.status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Added:</span>
                  <span className="font-medium">
                    {new Date(phone.created_at).toLocaleDateString()}
                  </span>
                </div>

                {phone.last_connected_at && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Last Connected:</span>
                    <span className="font-medium">
                      {new Date(phone.last_connected_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>

              {isAdmin && (
                <div className="mt-4 pt-4 border-t border-gray-200 space-y-2">
                  {phone.status === 'disconnected' && (
                    <button
                      onClick={() => handleConnect(phone)}
                      disabled={connectMutation.isPending}
                      className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:bg-gray-400"
                    >
                      <QrCode className="w-4 h-4" />
                      {connectMutation.isPending ? 'Generating QR...' : 'Connect WhatsApp'}
                    </button>
                  )}

                  {phone.status === 'connected' && (
                    <button
                      onClick={() => handleDisconnect(phone)}
                      disabled={disconnectMutation.isPending}
                      className="w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:bg-gray-400"
                    >
                      <XCircle className="w-4 h-4" />
                      {disconnectMutation.isPending ? 'Disconnecting...' : 'Disconnect'}
                    </button>
                  )}

                  {phone.status === 'connecting' && (
                    <button
                      onClick={() => {
                        setSelectedPhone(phone);
                        setShowQRModal(true);
                      }}
                      className="w-full bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2"
                    >
                      <QrCode className="w-4 h-4" />
                      Show QR Code
                    </button>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <AddPhoneModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        workspaceId={currentWorkspace.id}
      />

      <QRCodeModal
        isOpen={showQRModal}
        onClose={() => setShowQRModal(false)}
        phone={selectedPhone}
      />

      <DeletePhoneModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setSelectedPhone(null);
        }}
        phone={selectedPhone}
        workspaceId={currentWorkspace.id}
      />
    </div>
  );
};