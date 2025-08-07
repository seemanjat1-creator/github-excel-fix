import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

// ✅ Axios instance
const API = axios.create({
  baseURL: 'http://localhost:8000', // 🔁 Replace with your deployed FastAPI backend if needed
});

// ✅ User type
interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_admin: boolean;
  is_admin: boolean;
}

// ✅ Auth context shape
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    full_name: string,
    role?: string
  ) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

// ✅ Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ✅ Provider component
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ✅ Fetch user details from token
  const fetchUser = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const response = await API.get('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
      toast.error('Session expired. Please log in again.');
      localStorage.removeItem('token');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  // ✅ Login function
  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true);

      const formData = new URLSearchParams();
      formData.append('username', email); // Must use 'username' as key
      formData.append('password', password);

      const response = await API.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const { access_token } = response.data;
      if (!access_token) throw new Error('No access token received');

      localStorage.setItem('token', access_token);
      await fetchUser();
    } catch (error) {
      console.error('Login error:', error);
      toast.error('Login failed. Please check credentials.');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };


  // ✅ Register function
  const register = async (
    email: string,
    password: string,
    full_name: string,
    role = 'member'
  ) => {
    try {
      setIsLoading(true);
      const response = await API.post('/auth/register', {
        email,
        password,
        full_name,
        role,
      });

      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      await fetchUser();
    } catch (error) {
      console.error('Registration error:', error);
      toast.error('Registration failed.');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // ✅ Logout function
  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    toast.success('Logged out successfully');
  };

  // ✅ Context value
  const value: AuthContextType = {
    user,
    isLoading,
    login,
    register,
    logout,
    isAuthenticated: !!user && !!localStorage.getItem('token'),
    isAdmin: user?.is_admin ?? false,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// ✅ Custom hook
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
