import React from 'react';
import { X, Trash2, AlertTriangle, Phone } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { phoneAPI } from '../../lib/api';
import toast from 'react-hot-toast';

interface DeletePhoneModalProps {
  isOpen: boolean;
  onClose: () => void;
  phone: any;
  workspaceId: string;
}

export const DeletePhoneModal: React.FC<DeletePhoneModalProps> = ({ 
  isOpen, 
  onClose, 
  phone,
  workspaceId 
}) => {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => phoneAPI.deletePhone(phone.id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['phones', workspaceId] });
      toast.success(data.message || 'Phone number deleted successfully');
      onClose();
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Failed to delete phone number';
      toast.error(errorMessage);
    },
  });

  const handleDelete = () => {
    deleteMutation.mutate();
  };

  if (!isOpen || !phone) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <Trash2 className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Delete Phone Number</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          <div className="flex items-start gap-4 mb-6">
            <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Are you sure you want to delete this phone number?
              </h3>
              <p className="text-gray-600 mb-4">
                This action cannot be undone. The phone number will be permanently removed from your workspace.
              </p>
            </div>
          </div>

          {/* Phone Details */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-gray-500" />
              <div>
                <p className="font-medium text-gray-900">{phone.phone_number}</p>
                <p className="text-sm text-gray-600">{phone.display_name || 'No display name'}</p>
                <p className="text-xs text-gray-500">Status: {phone.status}</p>
              </div>
            </div>
          </div>

          {/* Warning Messages */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-medium text-yellow-900 mb-1">Important Notes:</h4>
                <ul className="text-xs text-yellow-800 space-y-1">
                  <li>• The phone will be disconnected from WhatsApp if currently connected</li>
                  <li>• Any active chats using this number will be affected</li>
                  <li>• This action will be logged for audit purposes</li>
                  <li>• You can add the same number again later if needed</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              disabled={deleteMutation.isPending}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors disabled:bg-red-400 flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Phone Number'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};