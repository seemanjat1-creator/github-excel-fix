import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import { WorkspaceProvider } from './contexts/WorkspaceContext';
import { ProtectedRoute } from './components/Routes/ProtectedRoute';
import { MainLayout } from './components/Layout/MainLayout';
import { LoginForm } from './components/Auth/LoginForm';
import { RegisterForm } from './components/Auth/RegisterForm';
import { DashboardPage } from './components/Dashboard/DashboardPage';
import { ChatPage } from './components/Chat/ChatPage';
import { KnowledgeBasePage } from './components/KnowledgeBase/KnowledgeBasePage';
import { PhonePage } from './components/Phone/PhonePage';
import { TeamPage } from './components/Team/TeamPage';
import { WorkflowPage } from './components/Workflow/WorkflowPage';
import { SettingsPage } from './components/Settings/SettingsPage';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WorkspaceProvider>
          <Router>
            <div className="min-h-screen bg-gray-50">
              <Routes>
                <Route path="/login" element={<LoginForm />} />
                <Route path="/register" element={<RegisterForm />} />
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <MainLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard" element={<DashboardPage />} />
                  <Route path="chats" element={<ChatPage />} />
                  <Route path="knowledge-base" element={<KnowledgeBasePage />} />
                  <Route path="team" element={<TeamPage />} />
                  <Route path="phones" element={<PhonePage />} />
                  <Route path="workflows" element={<WorkflowPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                </Route>
              </Routes>
              <Toaster position="top-right" />
            </div>
          </Router>
        </WorkspaceProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;