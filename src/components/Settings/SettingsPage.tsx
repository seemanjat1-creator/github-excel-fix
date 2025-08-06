import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceAPI } from '../../lib/api';
import { 
  Settings, Save, RefreshCw, MessageSquare, Palette, 
  Globe, Zap, Brain, Shield, AlertCircle, CheckCircle,
  User, Building, MessageCircle, Sparkles
} from 'lucide-react';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';

export const SettingsPage: React.FC = () => {
  const { currentWorkspace, refreshWorkspaces, isCurrentUserAdmin } = useWorkspace();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  
  const [activeTab, setActiveTab] = useState('ai-settings');
  const [settings, setSettings] = useState<any>({
    // Style and Tone
    tone: 'polite',
    response_length: 'short',
    language: 'english',
    
    // Additional Options
    include_emojis: true,
    formal_style: false,
    friendly_approach: true,
    detailed_responses: false,
    
    // Advanced Features
    reply_suggestions: true,
    personalization: true,
    fallback_messaging: true,
    context_awareness: true,
    
    // Custom Settings
    system_prompt: 'You are a helpful WhatsApp AI assistant for customer support.',
    custom_instructions: '',
    greeting_message: '',
    fallback_message: "I'm sorry, I didn't understand that. Could you please rephrase your question?",
    
    // Business Context
    business_name: '',
    business_type: '',
    business_description: '',
    
    // Advanced
    max_response_tokens: 150,
    temperature: 0.7,
    use_knowledge_base: true,
    escalate_to_human: true,
  });

  const { data: workspaceDetails, isLoading } = useQuery({
    queryKey: ['workspace-details', currentWorkspace?.id],
    queryFn: () => workspaceAPI.getById(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });

  // Update settings when workspace details are loaded
  React.useEffect(() => {
    if (workspaceDetails?.ai_settings) {
      setSettings(workspaceDetails.ai_settings);
    }
  }, [workspaceDetails]);

  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: any) => {
      if (!currentWorkspace?.id) {
        return Promise.reject(new Error('No workspace selected'));
      }
      return workspaceAPI.update(currentWorkspace!.id, { ai_settings: newSettings });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-details', currentWorkspace?.id] });
      refreshWorkspaces();
      toast.success('Settings updated successfully');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Failed to update settings';
      toast.error(errorMessage);
    },
  });
  
  // const { mutate: updateWorkspace, isPending } = useMutation({
  //   mutationFn: async (data: { name: string; slug: string; description: string }) => {
  //     if (!currentWorkspace?.id) {
  //       toast.error('No workspace selected.');
  //       throw new Error('Missing workspace ID');
  //     }
  //     return await workspaceAPI.update(currentWorkspace.id, data);
  //   },
  //   onSuccess: async () => {
  //     toast.success('Workspace updated');
  //     await refreshWorkspaces();
  //   },
  //   onError: (error: any) => {
  //     toast.error('Update failed');
  //     console.error('Update error:', error);
  //   },
  // });

  // const handleSave = (e: React.FormEvent) => {
  //   e.preventDefault();
  //   updateWorkspace({ name, slug, description });
  // };
  // if (!currentWorkspace?.id) {
  //   toast.error("Workspace not loaded.");
  //   return;
  // }


  const handleSave = () => {
    // Validate settings before saving
    if (!settings.system_prompt || settings.system_prompt.trim().length < 10) {
      toast.error('System prompt must be at least 10 characters');
      return;
    }
    
    if (settings.max_response_tokens < 50 || settings.max_response_tokens > 500) {
      toast.error('Max response tokens must be between 50 and 500');
      return;
    }
    
    if (settings.temperature < 0 || settings.temperature > 1) {
      toast.error('Temperature must be between 0 and 1');
      return;
    }
    
    updateSettingsMutation.mutate(settings);
  };

  const handleReset = () => {
    if (workspaceDetails?.ai_settings) {
      setSettings(workspaceDetails.ai_settings);
      toast.success('Settings reset to saved values');
    }
  };

  const isAdmin = isCurrentUserAdmin;
  // if (!currentWorkspace) {
  //   return <div className="p-4 text-sm text-muted-foreground">Loading workspace...</div>;
  // }

  // if (!isAdmin && currentWorkspace.admin_id !== user?.id) {
  //   return (
  //     <div className="p-4 text-sm text-muted-foreground">
  //       You do not have permission to access settings for this workspace.
  //     </div>
  //   );
  // }

  // Debug admin status
  React.useEffect(() => {
    console.log('SettingsPage - Admin status:', {
      isAdmin,
      currentWorkspace: currentWorkspace?.id,
      user: user?.id,
      adminId: currentWorkspace?.admin_id
    });
  }, [isAdmin, currentWorkspace, user]);

  if (!currentWorkspace) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Settings className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspace Selected</h3>
            <p className="text-gray-600">Please select a workspace to manage settings</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-600">Workspace: {currentWorkspace.name}</p>
          </div>
        </div>
        
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-yellow-600" />
            <div>
              <h3 className="text-lg font-medium text-yellow-900 mb-2">Administrator Access Required</h3>
              <p className="text-yellow-800 mb-4">
                Only workspace administrators can modify AI settings and configurations.
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
      </div>
    );
  }

  const tabs = [
    { id: 'ai-settings', name: 'AI Settings', icon: Brain },
    { id: 'business', name: 'Business Info', icon: Building },
    { id: 'advanced', name: 'Advanced', icon: Zap },
  ];

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600">Workspace: {currentWorkspace.name}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={updateSettingsMutation.isPending}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {updateSettingsMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* AI Settings Tab */}
      {activeTab === 'ai-settings' && (
        <div className="space-y-8">
          {/* Style and Tone Section */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Palette className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Style and Tone</h2>
                <p className="text-gray-600">Customize conversation style for your WhatsApp AI chatbot.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Response Length */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Length</label>
                <select
                  value={settings.response_length}
                  onChange={(e) => setSettings({ ...settings, response_length: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <option value="short">Short answers</option>
                  <option value="medium">Medium answers</option>
                  <option value="long">Detailed answers</option>
                </select>
              </div>

              {/* Tone */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tone</label>
                <select
                  value={settings.tone}
                  onChange={(e) => setSettings({ ...settings, tone: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <option value="polite">Polite</option>
                  <option value="friendly">Friendly</option>
                  <option value="professional">Professional</option>
                  <option value="casual">Casual</option>
                </select>
              </div>

              {/* Language */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
                <select
                  value={settings.language}
                  onChange={(e) => setSettings({ ...settings, language: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <option value="english">English</option>
                  <option value="spanish">Spanish</option>
                  <option value="french">French</option>
                  <option value="german">German</option>
                  <option value="hindi">Hindi</option>
                  <option value="portuguese">Portuguese</option>
                  <option value="italian">Italian</option>
                </select>
              </div>
            </div>

            {/* Additional Options */}
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-700 mb-4">Additional Options</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.include_emojis}
                    onChange={(e) => setSettings({ ...settings, include_emojis: e.target.checked })}
                    className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Include emojis</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.friendly_approach}
                    onChange={(e) => setSettings({ ...settings, friendly_approach: e.target.checked })}
                    className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Friendly</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.formal_style}
                    onChange={(e) => setSettings({ ...settings, formal_style: e.target.checked })}
                    className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Formal</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.detailed_responses}
                    onChange={(e) => setSettings({ ...settings, detailed_responses: e.target.checked })}
                    className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Detailed responses</span>
                </label>
              </div>
            </div>
          </div>

          {/* Customization Options */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Customization Options</h2>
                <p className="text-gray-600">Configure the behavior and style of the AI chatbot in WhatsApp.</p>
              </div>
            </div>

            <div className="space-y-6">
              {/* Advanced Features */}
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">Emojis</h4>
                    <p className="text-sm text-gray-600">Include relevant emojis in the responses</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.include_emojis}
                      onChange={(e) => setSettings({ ...settings, include_emojis: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">Reply Suggestions</h4>
                    <p className="text-sm text-gray-600">Offer suggested replies to the user after a response</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.reply_suggestions}
                      onChange={(e) => setSettings({ ...settings, reply_suggestions: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">Personalization</h4>
                    <p className="text-sm text-gray-600">Tailor responses based on user history and preferences</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.personalization}
                      onChange={(e) => setSettings({ ...settings, personalization: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">Fallback Messaging</h4>
                    <p className="text-sm text-gray-600">Send a default message if the chatbot does not understand the query</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.fallback_messaging}
                      onChange={(e) => setSettings({ ...settings, fallback_messaging: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Custom Messages */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <MessageCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Custom Messages</h2>
                <p className="text-gray-600">Customize default messages and prompts.</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">System Prompt</label>
                <textarea
                  value={settings.system_prompt}
                  onChange={(e) => setSettings({ ...settings, system_prompt: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Define the AI's role and behavior..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Greeting Message</label>
                <input
                  type="text"
                  value={settings.greeting_message}
                  onChange={(e) => setSettings({ ...settings, greeting_message: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Hello! How can I help you today?"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Fallback Message</label>
                <input
                  type="text"
                  value={settings.fallback_message}
                  onChange={(e) => setSettings({ ...settings, fallback_message: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="I'm sorry, I didn't understand that..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Custom Instructions</label>
                <textarea
                  value={settings.custom_instructions}
                  onChange={(e) => setSettings({ ...settings, custom_instructions: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Additional instructions for the AI..."
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Business Info Tab */}
      {activeTab === 'business' && (
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <Building className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Business Information</h2>
              <p className="text-gray-600">Provide context about your business for better AI responses.</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Business Name</label>
              <input
                type="text"
                value={settings.business_name}
                onChange={(e) => setSettings({ ...settings, business_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Your business name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Business Type</label>
              <input
                type="text"
                value={settings.business_type}
                onChange={(e) => setSettings({ ...settings, business_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="e.g., E-commerce, Restaurant, Consulting"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Business Description</label>
              <textarea
                value={settings.business_description}
                onChange={(e) => setSettings({ ...settings, business_description: e.target.value })}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Describe your business, products, and services..."
              />
            </div>
          </div>
        </div>
      )}

      {/* Advanced Tab */}
      {activeTab === 'advanced' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Advanced Settings</h2>
                <p className="text-gray-600">Fine-tune AI behavior and performance.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Response Tokens: {settings.max_response_tokens}
                </label>
                <input
                  type="range"
                  min="50"
                  max="500"
                  value={settings.max_response_tokens}
                  onChange={(e) => setSettings({ ...settings, max_response_tokens: parseInt(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Short</span>
                  <span>Long</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Creativity (Temperature): {settings.temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={settings.temperature}
                  onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Conservative</span>
                  <span>Creative</span>
                </div>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.use_knowledge_base}
                  onChange={(e) => setSettings({ ...settings, use_knowledge_base: e.target.checked })}
                  className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <span className="ml-2 text-sm text-gray-700">Use Knowledge Base for responses</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.escalate_to_human}
                  onChange={(e) => setSettings({ ...settings, escalate_to_human: e.target.checked })}
                  className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <span className="ml-2 text-sm text-gray-700">Escalate complex queries to humans</span>
              </label>
            </div>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-medium text-yellow-900 mb-1">Advanced Settings Warning</h4>
                <p className="text-xs text-yellow-800">
                  These settings directly affect AI performance. Changes may impact response quality and speed.
                  Test thoroughly before applying to production conversations.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};