import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI } from '../../lib/api';
import { Send, MoreHorizontal, Search, Filter, MessageSquare } from 'lucide-react';
import { formatTime, formatDate } from '../../lib/utils';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import toast from 'react-hot-toast';

export const ChatPage: React.FC = () => {
  const [selectedChat, setSelectedChat] = useState<any>(null);
  const [message, setMessage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const queryClient = useQueryClient();
  const { currentWorkspace } = useWorkspace();

  const { data: chats, isLoading } = useQuery({
    queryKey: ['chats', currentWorkspace?.id],
    queryFn: () => chatAPI.getWorkspaceChats(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });

  const { data: chatDetails } = useQuery({
    queryKey: ['chat-details', selectedChat?.id],
    queryFn: () => chatAPI.getChatById(selectedChat?.id),
    enabled: !!selectedChat?.id,
  });

  const sendMessageMutation = useMutation({
    mutationFn: ({ chatId, content }: { chatId: string; content: string }) =>
      chatAPI.sendMessage(chatId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-details', selectedChat?.id] });
      queryClient.invalidateQueries({ queryKey: ['chats', currentWorkspace?.id] });
      setMessage('');
      toast.success('Message sent');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to send message';
      toast.error(errorMessage);
    },
  });

  const handleSendMessage = () => {
    if (!message.trim() || !selectedChat || sendMessageMutation.isPending) return;
    
    sendMessageMutation.mutate({
      chatId: selectedChat.id,
      content: message.trim(),
    });
  };

  const filteredChats = chats?.filter((chat: any) =>
    searchTerm === '' || 
    chat.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    chat.customer_phone?.includes(searchTerm.toLowerCase())
  ) || [];

  // Show no workspace state
  if (!currentWorkspace) {
    return (
      <div className="flex h-screen bg-gray-50 items-center justify-center">
        <div className="text-center">
          <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspace Selected</h3>
          <p className="text-gray-600">Please select a workspace to view chats</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Chat List */}
      <div className="w-1/3 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Chats</h1>
              <p className="text-sm text-gray-600">{currentWorkspace.name}</p>
            </div>
            <div className="flex items-center gap-2">
              <button className="p-2 hover:bg-gray-100 rounded-lg">
                <Search className="w-4 h-4 text-gray-600" />
              </button>
              <button className="p-2 hover:bg-gray-100 rounded-lg">
                <Filter className="w-4 h-4 text-gray-600" />
              </button>
              <button className="p-2 hover:bg-gray-100 rounded-lg">
                <MoreHorizontal className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          </div>
          
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search chats..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-4">Loading chats...</div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredChats.map((chat: any) => (
                <div
                  key={chat.id}
                  onClick={() => setSelectedChat(chat)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 ${
                    selectedChat?.id === chat.id ? 'bg-green-50 border-r-2 border-green-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-900">
                      {chat.customer_name || chat.customer_phone}
                    </h3>
                    <span className="text-xs text-gray-500">
                      {formatTime(chat.last_message_at || chat.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 truncate">
                    {chat.customer_phone}
                  </p>
                  <div className="flex items-center justify-between mt-2">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      chat.status === 'qualified' 
                        ? 'bg-green-100 text-green-800'
                        : chat.status === 'active'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {chat.status}
                    </span>
                    {chat.ai_enabled && (
                      <span className="text-xs text-green-600 font-medium">AI</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat Window */}
      <div className="flex-1 flex flex-col">
        {selectedChat ? (
          <>
            {/* Chat Header */}
            <div className="bg-white p-4 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium">
                    {(selectedChat.customer_name || selectedChat.customer_phone).charAt(0)}
                  </span>
                </div>
                <div>
                  <h2 className="font-medium text-gray-900">
                    {selectedChat.customer_name || selectedChat.customer_phone}
                  </h2>
                  <p className="text-sm text-gray-600">{selectedChat.customer_phone}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-sm ${
                  selectedChat.status === 'qualified' 
                    ? 'bg-green-100 text-green-800'
                    : selectedChat.status === 'active'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {selectedChat.status}
                </span>
                {selectedChat.ai_enabled && (
                  <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                    AI Enabled
                  </span>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {chatDetails?.messages?.map((msg: any) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.direction === 'outgoing' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      msg.direction === 'outgoing'
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="text-sm">{msg.content}</p>
                    <p className={`text-xs mt-1 ${
                      msg.direction === 'outgoing' ? 'text-green-100' : 'text-gray-500'
                    }`}>
                      {formatTime(msg.timestamp)}
                      {msg.is_ai_generated && (
                        <span className="ml-2 font-medium">AI</span>
                      )}
                    </p>
                  </div>
                </div>
              ))}
              {(!chatDetails?.messages || chatDetails.messages.length === 0) && (
                <div className="text-center py-8">
                  <p className="text-gray-500">No messages yet</p>
                  <p className="text-sm text-gray-400 mt-1">Start the conversation below</p>
                </div>
              )}
            </div>

            {/* Message Input */}
            <div className="bg-white p-4 border-t border-gray-200">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Type a message..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!message.trim() || sendMessageMutation.isPending}
                  className="p-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-300"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Send className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Select a chat to start messaging
              </h3>
              <p className="text-gray-600">
                Choose a chat from the list to view the conversation
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};