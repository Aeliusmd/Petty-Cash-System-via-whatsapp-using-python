'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { authenticatedFetch } from '@/utils/api';

interface Permission {
  id: number;
  code: string;
  name: string;
  description: string;
  category: string;
}

interface Role {
  id: number;
  code: string;
  name: string;
  description?: string;
  is_system_role: boolean;
  organization_id?: number;
  permissions: Permission[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

// Simplified Permission Packages for Non-Technical Users
const PERMISSION_PACKAGES = [
  {
    id: 'my_claims',
    label: 'My Claims & Profile',
    icon: '👤',
    description: 'Submit claims, view own history, manage own profile',
    codes: [
      'claims.create', 'claims.read.own', 'claims.update.own',
      'claims.delete.own', 'claims.appeal',
      'employees.read.own', 'employees.update.own'
    ]
  },
  {
    id: 'claims_admin',
    label: 'Claims Management',
    icon: '💰',
    description: 'View all claims, approve/reject, exports',
    codes: [
      'claims.read.team', 'claims.read.all', 'claims.update.all',
      'claims.delete.all', 'claims.approve', 'claims.reject', 
      'claims.export'
    ]
  },
  {
    id: 'employees_admin',
    label: 'Employee Management',
    icon: '👥',
    description: 'Add, list, modify, and deactivate employees',
    codes: [
      'employees.create', 'employees.read.all', 'employees.update.all',
      'employees.delete', 'employees.activate', 'employees.assign_role'
    ]
  },
  {
    id: 'reports',
    label: 'Reports & Dashboard',
    icon: '📊',
    description: 'View financial reports and dashboards',
    codes: [
      'reports.view', 'reports.financial',
      'dashboard.view.team', 'dashboard.view.org'
    ]
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: '⚙️',
    description: 'Manage departments and claim categories',
    codes: ['config.view', 'config.manage']
  },
  {
    id: 'audit',
    label: 'Audit Logs',
    icon: '📋',
    description: 'View system audit logs',
    codes: ['audit.view']
  },
  {
    id: 'roles',
    label: 'Role Management',
    icon: '🎭',
    description: 'Create and manage custom roles',
    codes: ['roles.read', 'roles.create', 'roles.update', 'roles.delete']
  }
];

// Helper to check if a role/selection has a package
const hasPackage = (packageId: string, activeCodes: string[]) => {
  const pkg = PERMISSION_PACKAGES.find(p => p.id === packageId);
  if (!pkg) return false;
  // If the package has codes, check if ALL of them are present
  // We use "every" for strict matching, so a package is only "on" if fully supported
  return pkg.codes.every(code => activeCodes.includes(code));
};

const getPackagesForRole = (permissions: Permission[]) => {
  const roleCodes = permissions.map(p => p.code);
  return PERMISSION_PACKAGES.filter(pkg => hasPackage(pkg.id, roleCodes));
};

export default function RolesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, hasPermission, token } = useAuth();
  
  const [roles, setRoles] = useState<Role[]>([]);
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [processing, setProcessing] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
  });
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);

  // Permission check
  const canManageRoles = hasPermission('roles.create') || hasPermission('roles.update');

  useEffect(() => {
    if (isLoading) return;
    
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    
    if (!hasPermission('roles.read')) {
      router.push('/');
      return;
    }

    fetchRoles();
    fetchPermissions();
  }, [isLoading, isAuthenticated, router, token]);

  async function fetchRoles() {
    try {
      setLoading(true);
      const res = await authenticatedFetch(`${API_BASE_URL}/api/roles`);
      if (!res.ok) throw new Error('Failed to fetch roles');
      const data = await res.json();
      setRoles(data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load roles');
    } finally {
      setLoading(false);
    }
  }

  async function fetchPermissions() {
    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/roles/permissions`);
      if (!res.ok) throw new Error('Failed to fetch permissions');
      const data = await res.json();
      setAllPermissions(data || []);
    } catch (err) {
      console.error('Failed to load permissions:', err);
    }
  }

  function openCreateModal() {
    setEditingRole(null);
    setFormData({ code: '', name: '', description: '' });
    setSelectedPermissions([]);
    setShowModal(true);
  }

  function openEditModal(role: Role) {
    setEditingRole(role);
    setFormData({
      code: role.code,
      name: role.name,
      description: role.description || '',
    });
    setSelectedPermissions(role.permissions.map(p => p.code));
    setShowModal(true);
  }

  function togglePackage(pkgId: string) {
    const pkg = PERMISSION_PACKAGES.find(p => p.id === pkgId);
    if (!pkg) return;

    const isActive = hasPackage(pkgId, selectedPermissions);

    if (isActive) {
      // Remove all codes from this package
      setSelectedPermissions(prev => prev.filter(c => !pkg.codes.includes(c)));
    } else {
      // Add all codes (some might already be there, Set handles uniqueness later)
      setSelectedPermissions(prev => [...new Set([...prev, ...pkg.codes])]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setProcessing(true);

    try {
      // const token = sessionStorage.getItem('auth_token');
      const payload = {
        ...formData,
        permission_codes: selectedPermissions,
      };

      const url = editingRole 
        ? `${API_BASE_URL}/api/roles/${editingRole.id}`
        : `${API_BASE_URL}/api/roles`;

      const res = await authenticatedFetch(url, {
        method: editingRole ? 'PUT' : 'POST',
        headers: { 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to save role');
      }

      setShowModal(false);
      fetchRoles();
      alert(editingRole ? '✅ Role updated!' : '✅ Role created!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save role');
    } finally {
      setProcessing(false);
    }
  }

  async function handleDelete(role: Role) {
    if (role.code === 'super_admin') {
      alert('Cannot delete Super Admin role');
      return;
    }
    
    if (!confirm(`Are you sure you want to delete the role "${role.name}"?`)) return;

    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/roles/${role.id}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to delete role');
      }

      fetchRoles();
      alert('✅ Role deleted');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete role');
    }
  }



  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Role Management</h2>
          <p className="text-gray-600">Create and manage custom roles with specific permissions</p>
        </div>
        {canManageRoles && (
          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            + Create Role
          </button>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600">
          {error}
        </div>
      )}

      {/* Roles Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {roles.map((role) => (
          <div key={role.id} className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">{role.name}</h3>
                <p className="text-sm text-gray-500 font-mono">{role.code}</p>
              </div>
              {role.code === 'super_admin' && (
                <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded-full">
                  System
                </span>
              )}
            </div>
            
            {role.description && (
              <p className="text-gray-600 text-sm mb-4">{role.description}</p>
            )}
            
            {/* Permissions Summary using Packages */}
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-500 uppercase mb-2">
                Access Areas
              </p>
              <div className="flex flex-wrap gap-2">
                {getPackagesForRole(role.permissions).length > 0 ? (
                  getPackagesForRole(role.permissions).map((pkg) => (
                    <span 
                      key={pkg.id} 
                      className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs font-medium rounded border border-indigo-100 flex items-center gap-1"
                      title={pkg.description}
                    >
                      <span>{pkg.icon}</span>
                      {pkg.label}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-400 italic">Custom / No standard packages</span>
                )}
              </div>
            </div>
            
            {/* Actions - Allow edit/delete for all roles except super_admin */}
            {canManageRoles && role.code !== 'super_admin' && (
              <div className="flex gap-2 pt-4 border-t">
                <button
                  onClick={() => openEditModal(role)}
                  className="flex-1 px-3 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                >
                  ✏️ Edit
                </button>
                <button
                  onClick={() => handleDelete(role)}
                  className="flex-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                >
                  🗑️ Delete
                </button>
              </div>
            )}
            {role.code === 'super_admin' && (
              <p className="text-xs text-gray-400 pt-4 border-t text-center">
                Super Admin role cannot be modified
              </p>
            )}
          </div>
        ))}
      </div>

      {roles.length === 0 && !loading && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-4xl mb-4">🎭</p>
          <p>No custom roles yet. Create one to get started!</p>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-6">
                {editingRole ? 'Edit Role' : 'Create New Role'}
              </h3>
              
              <form onSubmit={handleSubmit}>
                {/* Role Details */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Role Code *
                    </label>
                    <input
                      type="text"
                      value={formData.code}
                      onChange={(e) => setFormData({...formData, code: e.target.value.toUpperCase()})}
                      required
                      disabled={!!editingRole}
                      placeholder="e.g., FINANCE_VIEWER"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Role Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      required
                      placeholder="e.g., Finance Viewer"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
                
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    placeholder="Describe what this role is for..."
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                {/* Permissions Selection (Packages) */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Access Permissions
                  </label>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {PERMISSION_PACKAGES.map((pkg) => {
                      const isSelected = hasPackage(pkg.id, selectedPermissions);
                      
                      return (
                        <label 
                          key={pkg.id}
                          className={`
                            relative flex items-start p-3 rounded-lg border cursor-pointer transition-all
                            ${isSelected 
                              ? 'bg-indigo-50 border-indigo-200 shadow-sm' 
                              : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                            }
                          `}
                        >
                          <div className="flex items-center h-5">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => togglePackage(pkg.id)}
                              className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
                            />
                          </div>
                          <div className="ml-3 text-sm">
                            <div className={`font-medium ${isSelected ? 'text-indigo-900' : 'text-gray-900'}`}>
                              {pkg.icon} {pkg.label}
                            </div>
                            <p className={`text-xs mt-1 ${isSelected ? 'text-indigo-700' : 'text-gray-500'}`}>
                              {pkg.description}
                            </p>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>
                
                {/* Form Actions */}
                <div className="flex gap-4 pt-4 border-t">
                  <button
                    type="submit"
                    disabled={processing}
                    className="flex-1 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {processing ? 'Saving...' : (editingRole ? 'Update Role' : 'Create Role')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
