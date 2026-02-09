'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

interface Unit {
  id: number;
  code: string;
  name: string;
  organization_id: number;
  is_active: boolean;
}

interface Category {
  id: number;
  code: string;
  name: string;
  description?: string;
  requires_receipt: boolean;
  display_order: number;
  unit_id?: number;
  is_active: boolean;
  prompt_message?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function SettingsPage() {
  const router = useRouter();
  const { user, token, isLoading, hasPermission } = useAuth();
  const [activeTab, setActiveTab] = useState<'departments' | 'categories'>('departments');
  const [accessDenied, setAccessDenied] = useState(false);

  // Departments state
  const [departments, setDepartments] = useState<Unit[]>([]);
  const [loadingDepts, setLoadingDepts] = useState(true);
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [editingDept, setEditingDept] = useState<Unit | null>(null);
  const [deptFormData, setDeptFormData] = useState({ code: '', name: '' });

  // Categories state
  const [selectedDeptId, setSelectedDeptId] = useState<number | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loadingCats, setLoadingCats] = useState(false);
  const [showCatModal, setShowCatModal] = useState(false);
  const [editingCat, setEditingCat] = useState<Category | null>(null);
  const [catFormData, setCatFormData] = useState({
    code: '',
    name: '',
    description: '',
    requires_receipt: false,
    display_order: 0,
    prompt_message: ''
  });

  // Permission-based access - allow view or manage
  const canViewConfig = hasPermission('config.view');
  const canManageConfig = hasPermission('config.manage');
  const hasConfigAccess = canViewConfig || canManageConfig;

  useEffect(() => {
    console.log('Settings Page Debug:', {
      isLoading,
      userExists: !!user,
      u_role: user?.role,
      u_permissions: user?.permissions,
      u_org_id: user?.organization_id,
      canView: canViewConfig,
      canManage: canManageConfig,
      hasAccess: hasConfigAccess
    });

    if (isLoading) return;

    if (!hasConfigAccess || !user?.organization_id) {
      console.warn('Access Denied: Missing permissions or org_id');
      setAccessDenied(true);
      // Removed timeout redirect for debugging
      // setTimeout(() => router.push('/'), 2000);
      return;
    }

    fetchDepartments();
  }, [hasConfigAccess, user, isLoading, router]);

import { authenticatedFetch } from '@/utils/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function SettingsPage() {
  const router = useRouter();
  const { user, token, isLoading, hasPermission } = useAuth();
  const [activeTab, setActiveTab] = useState<'departments' | 'categories'>('departments');
  const [accessDenied, setAccessDenied] = useState(false);

  // Departments state
  const [departments, setDepartments] = useState<Unit[]>([]);
  const [loadingDepts, setLoadingDepts] = useState(true);
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [editingDept, setEditingDept] = useState<Unit | null>(null);
  const [deptFormData, setDeptFormData] = useState({ code: '', name: '' });

  // Categories state
  const [selectedDeptId, setSelectedDeptId] = useState<number | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loadingCats, setLoadingCats] = useState(false);
  const [showCatModal, setShowCatModal] = useState(false);
  const [editingCat, setEditingCat] = useState<Category | null>(null);
  const [catFormData, setCatFormData] = useState({
    code: '',
    name: '',
    description: '',
    requires_receipt: false,
    display_order: 0,
    prompt_message: ''
  });

  // Permission-based access - allow view or manage
  const canViewConfig = hasPermission('config.view');
  const canManageConfig = hasPermission('config.manage');
  const hasConfigAccess = canViewConfig || canManageConfig;

  useEffect(() => {
    console.log('Settings Page Debug:', {
      isLoading,
      userExists: !!user,
      u_role: user?.role,
      u_permissions: user?.permissions,
      u_org_id: user?.organization_id,
      canView: canViewConfig,
      canManage: canManageConfig,
      hasAccess: hasConfigAccess
    });

    if (isLoading) return;

    if (!hasConfigAccess || !user?.organization_id) {
      console.warn('Access Denied: Missing permissions or org_id');
      setAccessDenied(true);
      // Removed timeout redirect for debugging
      // setTimeout(() => router.push('/'), 2000);
      return;
    }

    fetchDepartments();
  }, [hasConfigAccess, user, isLoading, router]);

  const fetchDepartments = async () => {
    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/units?organization_id=${user?.organization_id}`);
      const data = await res.json();
      setDepartments(data.units || []);
    } catch (error) {
      console.error('Error fetching departments:', error);
      setDepartments([]);
    } finally {
      setLoadingDepts(false);
    }
  };

  const fetchCategories = async (deptId: number) => {
    setLoadingCats(true);
    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/categories?unit_id=${deptId}`);
      const data = await res.json();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
      setCategories([]);
    } finally {
      setLoadingCats(false);
    }
  };

  const handleDeptSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const url = editingDept
        ? `${API_BASE_URL}/api/units/${editingDept.id}`
        : `${API_BASE_URL}/api/units`;

      const payload = {
        ...deptFormData,
        organization_id: user?.organization_id
      };

      const res = await authenticatedFetch(url, {
        method: editingDept ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        fetchDepartments();
        setShowDeptModal(false);
        setEditingDept(null);
        setDeptFormData({ code: '', name: '' });
      } else {
        const error = await res.json();
        alert(`Error: ${error.detail || 'Failed to save department'}`);
      }
    } catch (error) {
      console.error('Error saving department:', error);
      alert('Failed to save department');
    }
  };

  const handleDeptDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this department?')) return;

    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/units/${id}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        fetchDepartments();
        if (selectedDeptId === id) {
          setSelectedDeptId(null);
          setCategories([]);
        }
      }
    } catch (error) {
      console.error('Error deleting department:', error);
    }
  };

  const handleCatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeptId) return;

    try {
      const url = editingCat
        ? `${API_BASE_URL}/api/categories/${editingCat.id}`
        : `${API_BASE_URL}/api/categories`;

      const payload = {
        ...catFormData,
        unit_id: selectedDeptId
      };

      const res = await authenticatedFetch(url, {
        method: editingCat ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        fetchCategories(selectedDeptId);
        setShowCatModal(false);
        setEditingCat(null);
        setCatFormData({
          code: '',
          name: '',
          description: '',
          requires_receipt: false,
          display_order: 0,
          prompt_message: ''
        });
      } else {
        const error = await res.json();
        alert(`Error: ${error.detail || 'Failed to save category'}`);
      }
    } catch (error) {
      console.error('Error saving category:', error);
      alert('Failed to save category');
    }
  };

  const handleCatDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this category?')) return;

    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/categories/${id}`, {
        method: 'DELETE',
      });

      if (res.ok && selectedDeptId) {
        fetchCategories(selectedDeptId);
      }
    } catch (error) {
      console.error('Error deleting category:', error);
    }
  };

  if (accessDenied) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="text-red-500 text-6xl mb-4">🚫</div>
          <h1 className="text-2xl font-bold text-red-600 mb-2">Access Denied</h1>
          <p className="text-gray-600">Admin privileges required to access this page.</p>
          <p className="text-gray-400 text-sm mt-2">Redirecting to dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Tabs */}
      <div className="border-b border-gray-700 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('departments')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'departments'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-300'
            }`}
          >
            Departments
          </button>
          <button
            onClick={() => setActiveTab('categories')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'categories'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-300'
            }`}
          >
            Categories
          </button>
        </nav>
      </div>

      {/* Departments Tab */}
      {activeTab === 'departments' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Departments</h2>
            <button
              onClick={() => {
                setEditingDept(null);
                setDeptFormData({ code: '', name: '' });
                setShowDeptModal(true);
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              + Add Department
            </button>
          </div>

          {loadingDepts ? (
            <p>Loading...</p>
          ) : (

            <>
              {/* Desktop Table View */}
              <div className="hidden md:block bg-white shadow rounded-lg overflow-hidden mb-6">
                <table className="min-w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {departments.map((dept) => (
                      <tr key={dept.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap font-mono text-gray-700">{dept.code}</td>
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{dept.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 rounded text-xs ${dept.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {dept.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap space-x-2">
                          <button
                            onClick={() => {
                              setEditingDept(dept);
                              setDeptFormData({ code: dept.code, name: dept.name });
                              setShowDeptModal(true);
                            }}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeptDelete(dept.id)}
                            className="text-red-600 hover:text-red-800"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile Card View (Departments) */}
              <div className="md:hidden space-y-4 mb-6">
                {departments.map((dept) => (
                  <div key={dept.id} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-bold text-gray-900">{dept.name}</h3>
                        <p className="text-xs font-mono text-gray-500">{dept.code}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${dept.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {dept.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="flex justify-end gap-4 mt-3 pt-3 border-t border-gray-50">
                      <button
                        onClick={() => {
                          setEditingDept(dept);
                          setDeptFormData({ code: dept.code, name: dept.name });
                          setShowDeptModal(true);
                        }}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeptDelete(dept.id)}
                        className="text-sm text-red-600 hover:text-red-800 font-medium"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Categories Tab */}
      {activeTab === 'categories' && (
        <div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Select Department</label>
            <select
              value={selectedDeptId || ''}
              onChange={(e) => {
                const deptId = parseInt(e.target.value);
                setSelectedDeptId(deptId);
                fetchCategories(deptId);
              }}
              className="border rounded px-3 py-2 w-full md:w-64"
            >
              <option value="">-- Select Department --</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name} ({dept.code})
                </option>
              ))}
            </select>
          </div>

          {selectedDeptId && (
            <>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Categories</h2>
                <button
                  onClick={() => {
                    setEditingCat(null);
                    setCatFormData({
                      code: '',
                      name: '',
                      description: '',
                      requires_receipt: false,
                      display_order: 0,
                      prompt_message: ''
                    });
                    setShowCatModal(true);
                  }}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm md:text-base"
                >
                  + Add Category
                </button>
              </div>

              {loadingCats ? (
                <p>Loading...</p>
              ) : (
                <>
                  {/* Desktop Table View */}
                  <div className="hidden md:block bg-white shadow rounded-lg overflow-hidden">
                    <table className="min-w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Receipt Required</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Order</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {categories.map((cat) => (
                          <tr key={cat.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap font-mono text-gray-700">{cat.code}</td>
                            <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{cat.name}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {cat.requires_receipt ? '✅ Yes' : '❌ No'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">{cat.display_order}</td>
                            <td className="px-6 py-4 whitespace-nowrap space-x-2">
                              <button
                                onClick={() => {
                                  setEditingCat(cat);
                                  setCatFormData({
                                    code: cat.code,
                                    name: cat.name,
                                    description: cat.description || '',
                                    requires_receipt: cat.requires_receipt,
                                    display_order: cat.display_order,
                                    prompt_message: cat.prompt_message || ''
                                  });
                                  setShowCatModal(true);
                                }}
                                className="text-blue-600 hover:text-blue-800"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleCatDelete(cat.id)}
                                className="text-red-600 hover:text-red-800"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Mobile Card View (Categories) */}
                  <div className="md:hidden space-y-4">
                    {categories.map((cat) => (
                      <div key={cat.id} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h3 className="font-bold text-gray-900 text-lg">{cat.name}</h3>
                            <p className="text-xs font-mono text-gray-500">{cat.code}</p>
                          </div>
                          <div>
                            {cat.requires_receipt && (
                                <span className="bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded-full font-medium">
                                  Receipt Req.
                                </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="text-sm text-gray-600 mb-2">
                           {cat.description || 'No description'}
                        </div>
                        
                        <div className="flex justify-between items-center mt-3 pt-3 border-t border-gray-50">
                          <span className="text-xs text-gray-400">Order: {cat.display_order}</span>
                          <div className="flex gap-4">
                            <button
                              onClick={() => {
                                setEditingCat(cat);
                                setCatFormData({
                                  code: cat.code,
                                  name: cat.name,
                                  description: cat.description || '',
                                  requires_receipt: cat.requires_receipt,
                                  display_order: cat.display_order,
                                  prompt_message: cat.prompt_message || ''
                                });
                                setShowCatModal(true);
                              }}
                              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleCatDelete(cat.id)}
                              className="text-sm text-red-600 hover:text-red-800 font-medium"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                     {categories.length === 0 && (
                      <div className="text-center py-8 text-gray-500 bg-white rounded-xl border border-dashed border-gray-300">
                        No categories found in this department.
                      </div>
                    )}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}

      {/* Department Modal */}
      {showDeptModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[85vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              {editingDept ? 'Edit Department' : 'Add Department'}
            </h2>
            <form onSubmit={handleDeptSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Code</label>
                <input
                  type="text"
                  value={deptFormData.code}
                  onChange={(e) => setDeptFormData({ ...deptFormData, code: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Name</label>
                <input
                  type="text"
                  value={deptFormData.name}
                  onChange={(e) => setDeptFormData({ ...deptFormData, name: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowDeptModal(false);
                    setEditingDept(null);
                    setDeptFormData({ code: '', name: '' });
                  }}
                  className="px-4 py-2 border rounded hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  {editingDept ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Category Modal */}
      {showCatModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg max-h-[85vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              {editingCat ? 'Edit Category' : 'Add Category'}
            </h2>
            <form onSubmit={handleCatSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Code</label>
                <input
                  type="text"
                  value={catFormData.code}
                  onChange={(e) => setCatFormData({ ...catFormData, code: e.target.value.toUpperCase() })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Name</label>
                <input
                  type="text"
                  value={catFormData.name}
                  onChange={(e) => setCatFormData({ ...catFormData, name: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Description</label>
                <textarea
                  value={catFormData.description}
                  onChange={(e) => setCatFormData({ ...catFormData, description: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  rows={2}
                />
              </div>
              <div className="mb-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={catFormData.requires_receipt}
                    onChange={(e) => setCatFormData({ ...catFormData, requires_receipt: e.target.checked })}
                    className="mr-2"
                  />
                  <span className="text-sm font-medium">Requires Receipt</span>
                </label>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Prompt Message (WhatsApp)</label>
                <textarea
                  value={catFormData.prompt_message}
                  onChange={(e) => setCatFormData({ ...catFormData, prompt_message: e.target.value })}
                  className="w-full border rounded px-3 py-2 font-mono text-sm"
                  rows={8}
                  placeholder="Custom message shown to users when they select this category...&#10;&#10;Example:&#10;📦 Daily Allowance Claim&#10;&#10;Please provide:&#10;• Date of travel&#10;• Location/Route&#10;• Purpose"
                />
                <p className="text-xs text-gray-500 mt-1">Leave empty to use default prompt. Use \n for line breaks.</p>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Display Order</label>
                <input
                  type="number"
                  value={catFormData.display_order}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    setCatFormData({ ...catFormData, display_order: isNaN(val) ? 0 : val });
                  }}
                  className="w-full border rounded px-3 py-2"
                  min="0"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCatModal(false);
                    setEditingCat(null);
                    setCatFormData({
                      code: '',
                      name: '',
                      description: '',
                      requires_receipt: false,
                      display_order: 0,
                      prompt_message: ''
                    });
                  }}
                  className="px-4 py-2 border rounded hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  {editingCat ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
