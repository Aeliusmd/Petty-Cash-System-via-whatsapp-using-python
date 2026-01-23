'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

interface User {
  id: number;
  name: string;
  employee_code?: string;
  role: 'super_admin' | 'admin' | 'manager' | 'employee';
  is_super_admin?: boolean;  // Track original super admin status when inside org
  organization_id?: number;
  organization_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, userData: User) => void;
  logout: () => void;
  enterOrganization: (orgId: number) => Promise<void>;
  exitOrganization: () => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isManager: boolean;
  isSuperAdmin: boolean;
  isInOrganization: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load auth state from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');
    
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = (newToken: string, userData: User) => {
    setToken(newToken);
    setUser(userData);
    localStorage.setItem('auth_token', newToken);
    localStorage.setItem('auth_user', JSON.stringify(userData));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    router.push('/login');
  };

  const enterOrganization = async (orgId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/organizations/${orgId}/enter`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to enter organization');
      }

      const data = await res.json();
      
      // Update auth state with new token and user info
      setToken(data.access_token);
      setUser(data.employee);
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('auth_user', JSON.stringify(data.employee));
      
      // Navigate to dashboard
      router.push('/');
    } catch (error) {
      console.error('Error entering organization:', error);
      throw error;
    }
  };

  const exitOrganization = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/organizations/exit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to exit organization');
      }

      const data = await res.json();
      
      // Update auth state with new token (super_admin mode)
      setToken(data.access_token);
      setUser(data.employee);
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('auth_user', JSON.stringify(data.employee));
      
      // Navigate to organizations list
      router.push('/organizations');
    } catch (error) {
      console.error('Error exiting organization:', error);
      throw error;
    }
  };

  // Check both role AND is_super_admin flag (for when super admin is inside org)
  const isSuperAdmin = user?.role === 'super_admin' || user?.is_super_admin === true;
  const isInOrganization = !!user?.organization_id;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        enterOrganization,
        exitOrganization,
        isAuthenticated: !!token && !!user,
        isAdmin: user?.role === 'admin' || user?.role === 'super_admin',
        isManager: user?.role === 'manager' || user?.role === 'admin' || user?.role === 'super_admin',
        isSuperAdmin,
        isInOrganization,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
