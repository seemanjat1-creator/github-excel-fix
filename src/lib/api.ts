import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status !== 401) {
      console.error('API Error:', error.response?.data || error.message);
    }
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      if (
        !window.location.pathname.includes('/login') &&
        !window.location.pathname.includes('/register')
      ) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ------------------ APIs ------------------

export const authAPI = {
  login: async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
  register: async (data: { email: string; password: string; full_name: string; role?: string }) => {
    const response = await api.post('/auth/register', {
      email: data.email,
      password: data.password,
      full_name: data.full_name,
      role: data.role || 'member',
    });
    return response.data;
  },
  getProfile: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

export const workspaceAPI = {
  getAll: async () => {
    const response = await api.get('/workspaces');
    return response.data;
  },
  getById: async (id: string) => {
    const response = await api.get(`/workspaces/${id}`);
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/workspaces', data);
    return response.data;
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/workspaces/${id}`, data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/workspaces/${id}`);
    return response.data;
  },
  checkAdminAccess: async (workspaceId: string) => {
    const response = await api.get(`/workspaces/${workspaceId}`);
    return response.data;
  },
  getTeamMembers: async (workspaceId: string) => {
    const response = await api.get(`/workspaces/${workspaceId}/members`);
    return response.data;
  },
  addMember: async (workspaceId: string, email: string) => {
    const response = await api.post(`/workspaces/${workspaceId}/members`, { member_email: email });
    return response.data;
  },
  makeAdminOfAllWorkspaces: async () => {
    const response = await api.post('/workspaces/make-admin');
    return response.data;
  },
  removeMember: async (workspaceId: string, memberId: string) => {
    const response = await api.delete(`/workspaces/${workspaceId}/members/${memberId}`);
    return response.data;
  },
};

export const userAPI = {
  getAll: async () => {
    const response = await api.get('/users');
    return response.data;
  },
  getById: async (id: string) => {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },
};

export const chatAPI = {
  getWorkspaceChats: async (workspaceId: string) => {
    const response = await api.get(`/chats/workspace/${workspaceId}`);
    return response.data;
  },
  getChatById: async (chatId: string) => {
    const response = await api.get(`/chats/${chatId}`);
    return response.data;
  },
  sendMessage: async (chatId: string, content: string) => {
    const response = await api.post(`/chats/${chatId}/messages`, {
      content,
      direction: 'outgoing',
      message_type: 'text',
    });
    return response.data;
  },
  getQualifiedLeads: async (workspaceId: string) => {
    const response = await api.get(`/chats/qualified-leads/${workspaceId}`);
    return response.data;
  },
  updateChatStatus: async (chatId: string, status: string) => {
    const response = await api.put(`/chats/${chatId}/status`, { status });
    return response.data;
  },
};

export const phoneAPI = {
  getWorkspacePhones: async (workspaceId: string) => {
    const response = await api.get(`/phones/workspace/${workspaceId}`);
    return response.data;
  },
  addPhone: async (workspaceId: string, phoneNumber: string, displayName?: string) => {
    const response = await api.post(`/phones`, {
      workspace_id: workspaceId,
      phone_number: phoneNumber.trim(),
      display_name: displayName,
    });
    return response.data;
  },
  connectPhone: async (phoneId: string) => {
    const response = await api.post(`/phones/${phoneId}/connect`);
    return response.data;
  },
  disconnectPhone: async (phoneId: string) => {
    const response = await api.post(`/phones/${phoneId}/disconnect`);
    return response.data;
  },
  getPhoneStatus: async (phoneId: string) => {
    const response = await api.get(`/phones/${phoneId}/status`);
    return response.data;
  },
  deletePhone: async (phoneId: string) => {
    const response = await api.delete(`/phones/${phoneId}`);
    return response.data;
  },
  deletePhoneByNumber: async (workspaceId: string, phoneNumber: string) => {
    const response = await api.delete(
      `/phones/workspace/${workspaceId}/phone/${phoneNumber}`
    );
    return response.data;
  },
};

export const documentAPI = {
  getWorkspaceDocuments: async (
    workspaceId: string,
    documentType?: string,
    status?: string,
    search?: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const params = new URLSearchParams();
    if (documentType) params.append('document_type', documentType);
    if (status) params.append('status', status);
    if (search) params.append('search', search);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const response = await api.get(`/documents/workspace/${workspaceId}?${params}`);
    return response.data;
  },
  getDocumentStats: async (workspaceId: string) => {
    const response = await api.get(`/documents/workspace/${workspaceId}/stats`);
    return response.data;
  },
  getDocumentById: async (documentId: string) => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },
  uploadDocument: async (
    workspaceId: string,
    file: File,
    title?: string,
    description?: string,
    tags?: string[]
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('workspace_id', workspaceId);
    if (title) formData.append('title', title.trim());
    if (description) formData.append('description', description.trim());
    if (tags?.length) formData.append('tags', tags.join(','));

    const response = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  updateDocument: async (documentId: string, data: any) => {
    const response = await api.put(`/documents/${documentId}`, data);
    return response.data;
  },
  deleteDocument: async (documentId: string) => {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  },
  searchDocuments: async (searchRequest: any) => {
    const response = await api.post('/documents/search', {
      query: searchRequest.query.trim(),
      workspace_id: searchRequest.workspace_id,
      limit: searchRequest.limit || 5,
      similarity_threshold: searchRequest.similarity_threshold || 0.7,
      document_types: searchRequest.document_types,
      tags: searchRequest.tags,
    });
    return response.data;
  },
  getSearchSuggestions: async (
    workspaceId: string,
    query: string,
    limit: number = 5
  ) => {
    const response = await api.get(
      `/documents/search/suggestions/${workspaceId}?query=${encodeURIComponent(query)}&limit=${limit}`
    );
    return response.data;
  },
};

export const workflowAPI = {
  getWorkspaceSteps: async (workspaceId: string) => {
    const response = await api.get(`/workflows/workspace/${workspaceId}`);
    return response.data;
  },
  createStep: async (data: any) => {
    const response = await api.post('/workflows', data);
    return response.data;
  },
  updateStep: async (stepId: string, data: any) => {
    const response = await api.put(`/workflows/${stepId}`, data);
    return response.data;
  },
  deleteStep: async (stepId: string) => {
    const response = await api.delete(`/workflows/${stepId}`);
    return response.data;
  },
  reorderSteps: async (workspaceId: string, stepOrders: any[]) => {
    const response = await api.post('/workflows/reorder', {
      workspace_id: workspaceId,
      step_orders: stepOrders,
    });
    return response.data;
  },
  getChatProgress: async (chatId: string) => {
    const response = await api.get(`/workflows/progress/${chatId}`);
    return response.data;
  },
};

export default api;
