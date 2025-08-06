import React from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Phone, Plus } from 'lucide-react';
import { phoneAPI } from '../../lib/api';
import toast from 'react-hot-toast';

const schema = yup.object({
  phone_number: yup
    .string()
    .required('Phone number is required')
    .matches(/^\+?[1-9]\d{1,14}$/, 'Please enter a valid phone number with country code'),
  display_name: yup.string().optional(),
});

type FormData = yup.InferType<typeof schema>;

interface AddPhoneModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
}

export const AddPhoneModal: React.FC<AddPhoneModalProps> = ({ isOpen, onClose, workspaceId }) => {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormData>({
    resolver: yupResolver(schema),
  });

  const addPhoneMutation = useMutation({
    mutationFn: (data: FormData) => phoneAPI.addPhone(workspaceId, data.phone_number, data.display_name),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['phones', workspaceId] });
      toast.success('Phone number added successfully');
      reset();
      onClose();
      
      // Automatically trigger connection after adding
      setTimeout(() => {
        phoneAPI.connectPhone(data.id).then((connectData) => {
          if (connectData.qr_code) {
            // Open QR code in new window/tab pointing to Node.js server
            const qrUrl = `${import.meta.env.VITE_WHATSAPP_SERVER_URL || 'http://localhost:3000'}/qr/${data.phone_number}`;
            window.open(qrUrl, '_blank', 'width=400,height=500,scrollbars=yes,resizable=yes');
            toast.success('QR code generated! Check the new window to scan.');
          }
        }).catch(() => {
          toast.error('Failed to generate QR code');
        });
      }, 1000);
    },
    onError: (error: any) => {
      let errorMessage = 'Failed to add phone number';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      toast.error(errorMessage);
    },
  });

  const onSubmit = (data: FormData) => {
    // Format phone number to ensure it has country code
    let formattedPhone = data.phone_number.trim();
    
    // Basic phone number validation
    if (!/^\+?[1-9]\d{1,14}$/.test(formattedPhone.replace(/[\s\-\(\)]/g, ''))) {
      toast.error('Please enter a valid phone number');
      return;
    }
    
    if (!formattedPhone.startsWith('+')) {
      formattedPhone = '+' + formattedPhone;
    }
    
    addPhoneMutation.mutate({
      ...data,
      phone_number: formattedPhone,
      display_name: data.display_name?.trim() || undefined,
    });
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
              <Phone className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Add Phone Number</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          <div>
            <label htmlFor="phone_number" className="block text-sm font-medium text-gray-700 mb-1">
              Phone Number *
            </label>
            <input
              {...register('phone_number')}
              type="tel"
              placeholder="+1234567890"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            {errors.phone_number && (
              <p className="mt-1 text-sm text-red-600">{errors.phone_number.message}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Include country code (e.g., +1 for US, +91 for India)
            </p>
          </div>

          <div>
            <label htmlFor="display_name" className="block text-sm font-medium text-gray-700 mb-1">
              Display Name
            </label>
            <input
              {...register('display_name')}
              type="text"
              placeholder="My Business WhatsApp"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            {errors.display_name && (
              <p className="mt-1 text-sm text-red-600">{errors.display_name.message}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Optional: A friendly name to identify this number
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">What happens next?</h4>
            <ol className="text-xs text-blue-800 space-y-1">
              <li>1. Phone number will be added to your workspace</li>
              <li>2. QR code will be generated automatically</li>
              <li>3. You'll be redirected to scan the QR code</li>
              <li>4. Once scanned, WhatsApp will be connected</li>
            </ol>
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
              disabled={addPhoneMutation.isPending}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors disabled:bg-gray-400 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {addPhoneMutation.isPending ? 'Adding...' : 'Add & Connect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};