import React, { useEffect, useState } from 'react';
import { X, QrCode, CheckCircle, RefreshCw, ExternalLink } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { phoneAPI } from '../../lib/api';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

interface QRCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  phone: any;
}

export const QRCodeModal: React.FC<QRCodeModalProps> = ({ isOpen, onClose, phone }) => {
  const [isConnected, setIsConnected] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Poll for phone status updates
  const { data: phoneStatus } = useQuery({
    queryKey: ['phone-status', phone?.id],
    queryFn: () => phoneAPI.getPhoneStatus(phone!.id),
    enabled: isOpen && !!phone?.id,
    refetchInterval: 3000, // Poll every 3 seconds
    retry: 1,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (phoneStatus?.status === 'connected' && !isConnected) {
      setIsConnected(true);
      toast.success('WhatsApp connected successfully!');
      
      // Refresh phone list
      queryClient.invalidateQueries({ queryKey: ['phones'] });
      
      // Auto-redirect to dashboard after 2 seconds
      setTimeout(() => {
        onClose();
        navigate('/dashboard');
      }, 2000);
    }
  }, [phoneStatus, isConnected, navigate, onClose, queryClient]);

  const handleOpenQR = () => {
    if (phone?.phone_number && phone.phone_number.trim()) {
      const qrUrl = `${import.meta.env.VITE_WHATSAPP_SERVER_URL || 'http://localhost:3000'}/qr/${phone.phone_number}`;
      window.open(qrUrl, '_blank', 'width=400,height=500,scrollbars=yes,resizable=yes');
    } else {
      toast.error('Invalid phone number');
    }
  };

  const handleClose = () => {
    setIsConnected(false);
    onClose();
  };

  if (!isOpen || !phone) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
              {isConnected ? (
                <CheckCircle className="w-4 h-4 text-white" />
              ) : (
                <QrCode className="w-4 h-4 text-white" />
              )}
            </div>
            <h2 className="text-lg font-semibold text-gray-900">
              {isConnected ? 'WhatsApp Connected!' : 'Connect WhatsApp'}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {isConnected ? (
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Successfully Connected!</h3>
              <p className="text-gray-600 mb-4">
                WhatsApp number {phone.phone_number} is now connected and ready to use.
              </p>
              <p className="text-sm text-gray-500">
                Redirecting to dashboard in a moment...
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <QrCode className="w-8 h-8 text-blue-600" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Scan QR Code</h3>
                <p className="text-gray-600 mb-4">
                  Open WhatsApp on your phone and scan the QR code to connect {phone.phone_number}
                </p>
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-700">Connection Status:</span>
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
                    <span className="text-sm text-blue-600">
                      {phoneStatus?.status === 'connecting' ? 'Waiting for scan...' : 'Generating...'}
                    </span>
                  </div>
                </div>
                
                <button
                  onClick={handleOpenQR}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open QR Code Page
                </button>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 className="text-sm font-medium text-yellow-900 mb-2">Instructions:</h4>
                <ol className="text-xs text-yellow-800 space-y-1">
                  <li>1. Click "Open QR Code Page" above</li>
                  <li>2. Open WhatsApp on your phone</li>
                  <li>3. Go to Settings → Linked Devices</li>
                  <li>4. Tap "Link a Device"</li>
                  <li>5. Scan the QR code displayed</li>
                  <li>6. Wait for connection confirmation</li>
                </ol>
              </div>

              <div className="text-center">
                <p className="text-xs text-gray-500">
                  This window will automatically close once connected
                </p>
              </div>
            </div>
          )}
        </div>

        {!isConnected && (
          <div className="px-6 pb-6">
            <button
              onClick={handleClose}
              className="w-full px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
};