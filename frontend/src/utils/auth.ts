/**
 * Authentication and Role Utilities
 * Helper functions for role-based access control in the frontend
 */

export type UserRole = 'employee' | 'manager' | 'admin' | 'super_admin';

export interface User {
  id: number;
  name: string;
  employee_code: string;
  role: UserRole;
}

/**
 * Get the current user from localStorage
 */
export const getCurrentUser = (): User | null => {
  if (typeof window === 'undefined') return null;
  
  try {
    const userJson = localStorage.getItem('user');
    if (!userJson) return null;
    return JSON.parse(userJson) as User;
  } catch {
    return null;
  }
};

/**
 * Get the current user's role
 */
export const getUserRole = (): UserRole => {
  const user = getCurrentUser();
  return user?.role || 'employee';
};

/**
 * Check if user is a super admin
 */
export const isSuperAdmin = (): boolean => {
  return getUserRole() === 'super_admin';
};

/**
 * Check if user is an admin (includes super_admin)
 */
export const isAdmin = (): boolean => {
  const role = getUserRole();
  return role === 'admin' || role === 'super_admin';
};

/**
 * Check if user is a manager (includes admin and super_admin)
 */
export const isManager = (): boolean => {
  const role = getUserRole();
  return role === 'manager' || role === 'admin' || role === 'super_admin';
};

/**
 * Get the authentication token
 */
export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = (): boolean => {
  return !!getToken();
};

/**
 * Clear authentication data (logout)
 */
export const clearAuth = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};

/**
 * Set authentication data after login
 */
export const setAuth = (token: string, user: User): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('token', token);
  localStorage.setItem('user', JSON.stringify(user));
};
