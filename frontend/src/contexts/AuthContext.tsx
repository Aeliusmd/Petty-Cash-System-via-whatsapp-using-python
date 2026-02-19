'use client';

import { createContext, useContext, useState, useEffect, useRef, ReactNode, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

interface User {
  id: number;
  name: string;
  employee_code?: string;
  role: 'super_admin' | 'admin' | 'manager' | 'employee' | 'staff' | 'finance';
  role_id?: number;
  permissions?: string[];  // New: Array of permission codes
  is_super_admin?: boolean;
  organization_id?: number;
  organization_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (accessToken: string, refreshToken: string, userData: User) => void;
  logout: () => void;
  enterOrganization: (orgId: number) => Promise<void>;
  exitOrganization: () => Promise<void>;
  isAuthenticated: boolean;
  // Legacy role-based checks (kept for backward compatibility)
  isAdmin: boolean;
  isManager: boolean;
  isSuperAdmin: boolean;
  isInOrganization: boolean;
  // New: Permission-based check
  hasPermission: (permissionCode: string) => boolean;
  hasAnyPermission: (permissionCodes: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const permissionPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Helper to schedule silent refresh
  const scheduleRefresh = useCallback((accessToken: string) => {
    try {
      // Decode token to get expiry
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const exp = payload.exp * 1000; // to ms
      const now = Date.now();
      const timeUntilExpiry = exp - now;
      
      // Refresh 5 minutes before expiry, but handle short-lived tokens
      // If token has > 5 mins left, refresh at (expiry - 5min)
      // If token has 1-5 mins left, refresh at (expiry - 30sec)
      // If token has < 1 min left, refresh immediately
      
      let refreshDelay = timeUntilExpiry - (5 * 60 * 1000);
      
      if (refreshDelay <= 0) {
          if (timeUntilExpiry > 60 * 1000) {
              // Token valid for more than 1 min but less than 5 mins
              // Refresh 30 seconds before expiry
              console.log('⚠️ Short-lived token detected, reducing buffer');
              refreshDelay = timeUntilExpiry - (30 * 1000);
          } else {
              // Less than 1 minute left, refresh now
              refreshDelay = 0;
          }
      }
      
      if (refreshDelay > 0) {
        console.log(`🔄 Scheduling token refresh in ${Math.round(refreshDelay/1000/60*10)/10} minutes (Expiry in ${Math.round(timeUntilExpiry/1000/60*10)/10} mins)`);
        // Clear any existing timer if we stored it (context doesn't store tracking ID currently, but usually safe in React if component doesn't unmount frequently)
        setTimeout(() => refreshSession(), refreshDelay);
      } else {
        // Already expired or close to, refresh immediately
        console.log('⏰ Token expiring immediately, refreshing now');
        refreshSession();
      }

    } catch (e) {
      console.error('Error scheduling refresh:', e);
    }
  }, []);

  // Silently refresh user data (permissions) from the server
  const refreshPermissions = useCallback(async (currentToken: string) => {
    if (!currentToken) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${currentToken}` }
      });
      if (res.ok) {
        const freshUserData = await res.json();
        setUser(freshUserData);
        localStorage.setItem('auth_user', JSON.stringify(freshUserData));
      } else if (res.status === 401) {
        // Token expired mid-session – try refresh
        await refreshSession();
      }
    } catch {
      // Network error – silently ignore, we'll retry next interval
    }
  }, []);

  const refreshSession = async () => {
    const storedRefreshToken = localStorage.getItem('refresh_token');
    if (!storedRefreshToken) return;

    try {
      console.log('🔄 Attempting to refresh session...');
      const res = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: storedRefreshToken })
      });

      if (res.ok) {
        const data = await res.json();
        console.log('✅ Session refreshed successfully');
        
        login(data.access_token, data.refresh_token, data.employee);
      } else {
        console.log('❌ Refresh failed, logging out');
        logout();
      }
    } catch (error) {
      console.error('Error refreshing session:', error);
      logout();
    }
  };

  // Load auth state from localStorage on mount and fetch fresh user data
  useEffect(() => {
    const loadAuthState = async () => {
      const storedToken = localStorage.getItem('auth_token');
      const storedRefreshToken = localStorage.getItem('refresh_token');
      const storedUser = localStorage.getItem('auth_user');
      
      if (storedToken && storedUser) {
        // Check if token is expired BEFORE setting state
        try {
            const payload = JSON.parse(atob(storedToken.split('.')[1]));
            const exp = payload.exp * 1000;
            const now = Date.now();
            
            // If token is already expired (not just expiring soon)
            if (now > exp) {
                console.log('🔴 Token expired, attempting refresh or logout');
                // Token expired, try refresh if we have a refresh token
                if (storedRefreshToken) {
                    await refreshSession();
                } else {
                    // No refresh token, clear everything and redirect to login
                    console.log('❌ No refresh token, clearing auth state');
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('refresh_token');
                    localStorage.removeItem('auth_user');
                }
                setIsLoading(false);
                return;
            }
            
            // Token is valid, set the state
            setToken(storedToken);
            setRefreshToken(storedRefreshToken);
            setUser(JSON.parse(storedUser));
            
            // If token is expiring soon (within 5 minutes), refresh it
            if (now > exp - (5 * 60 * 1000)) {
                console.log('⚠️ Token expiring soon, refreshing...');
                if (storedRefreshToken) {
                    await refreshSession();
                    setIsLoading(false);
                    return;
                }
            }
        } catch (e) {
            console.error("❌ Error checking token expiry, clearing auth state:", e);
            // If we can't parse the token, it's invalid - clear everything
            localStorage.removeItem('auth_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('auth_user');
            setIsLoading(false);
            return;
        }
        
        // Then fetch fresh user data with latest permissions
        try {
          const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });
          
          if (res.ok) {
            const freshUserData = await res.json();
            setUser(freshUserData);
            localStorage.setItem('auth_user', JSON.stringify(freshUserData));
            // Schedule refresh for the valid token
            scheduleRefresh(storedToken);
          } else if (res.status === 401) {
             // Token invalid, try refresh logic
             console.log('❌ 401 from /api/auth/me, attempting refresh');
             if (storedRefreshToken) {
                 await refreshSession();
             } else {
                 logout();
             }
          }
        } catch (error) {
          console.error('Failed to fetch fresh user data:', error);
        }
      }
      setIsLoading(false);
    };
    
    loadAuthState();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  const login = (accessToken: string, newRefreshToken: string, userData: User) => {
    setToken(accessToken);
    setRefreshToken(newRefreshToken);
    setUser(userData);
    
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('refresh_token', newRefreshToken);
    localStorage.setItem('auth_user', JSON.stringify(userData));
    
    // Schedule background refresh
    scheduleRefresh(accessToken);
  };

  // ── Background permission polling ─────────────────────────────────────────
  // Poll /api/auth/me every 30 s while the user is logged in so that
  // admin-side role/permission changes are reflected automatically.
  useEffect(() => {
    if (!token) {
      // Not logged in – clear any lingering interval
      if (permissionPollRef.current) {
        clearInterval(permissionPollRef.current);
        permissionPollRef.current = null;
      }
      return;
    }

    // Start polling
    const POLL_INTERVAL_MS = 30_000;

    const poll = () => {
      // Skip when the tab is hidden to save requests
      if (document.visibilityState === 'hidden') return;
      refreshPermissions(token);
    };

    permissionPollRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      if (permissionPollRef.current) {
        clearInterval(permissionPollRef.current);
        permissionPollRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]); // Re-run whenever token changes (login/logout)
  // ──────────────────────────────────────────────────────────────────────────


  const logout = () => {
    // Stop permission polling
    if (permissionPollRef.current) {
      clearInterval(permissionPollRef.current);
      permissionPollRef.current = null;
    }
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
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
      
      // Update auth state with new token and user info (includes permissions)
      // Now expects { access_token, refresh_token, employee, ... }
      login(data.access_token, data.refresh_token, data.employee);
      
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
      
      // Update auth state (includes permissions)
      login(data.access_token, data.refresh_token, data.employee);
      
      // Navigate to organizations list
      router.push('/organizations');
    } catch (error) {
      console.error('Error exiting organization:', error);
      throw error;
    }
  };

  // Permission check function
  const hasPermission = useCallback((permissionCode: string): boolean => {
    if (!user) return false;
    // Super admin has all permissions
    if (user.role === 'super_admin' || user.is_super_admin) return true;
    // Check permissions array
    return user.permissions?.includes(permissionCode) ?? false;
  }, [user]);

  // Check if user has any of the given permissions
  const hasAnyPermission = useCallback((permissionCodes: string[]): boolean => {
    return permissionCodes.some(code => hasPermission(code));
  }, [hasPermission]);

  // Legacy role checks (for backward compatibility)
  const isSuperAdmin = user?.role === 'super_admin' || user?.is_super_admin === true;
  const isInOrganization = !!user?.organization_id;
  
  // Legacy isAdmin/isManager - now also consider permissions for better flexibility
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin' || hasPermission('employees.read.all');
  const isManager = user?.role === 'manager' || isAdmin || hasPermission('claims.approve');

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
        isAdmin,
        isManager,
        isSuperAdmin,
        isInOrganization,
        hasPermission,
        hasAnyPermission,
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
