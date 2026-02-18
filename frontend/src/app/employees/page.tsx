'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { authenticatedFetch } from '@/utils/api';

interface Employee {
  id: number;
  employee_code: string;
  name: string;
  phone_number: string;
  email: string | null;
  role: string;
  is_active: boolean;
  grade_id: number | null;
  grade_code: string | null;
  grade_name: string | null;
  location_id: number | null;
  location_code: string | null;
  location_name: string | null;
  unit_id: number | null;
  unit_code: string | null;
  unit_name: string | null;
  manager_id: number | null;
  manager_name: string | null;
  spending_limit: number | null;
  spending_limit_period: string | null;
  spending_limit_custom_days: number | null;
}

interface Grade { id: number; code: string; name: string; }
interface Location { id: number; code: string; name: string; }
interface Unit { id: number; code: string; name: string; }
interface Role { id: number; code: string; name: string; }

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function EmployeesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, hasPermission } = useAuth();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [processing, setProcessing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [includeInactive, setIncludeInactive] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Form state
  const [formData, setFormData] = useState({
    employee_code: '',
    name: '',
    phone_number: '',
    email: '',
    grade_id: '',
    location_id: '',
    unit_id: '',
    manager_id: '',
    role: 'employee',
    spending_limit: '',
    spending_limit_period: 'monthly',
    spending_limit_custom_days: '',
  });

  // Permission-based access
  const canViewEmployees = hasPermission('employees.read.all');

  useEffect(() => {
    if (isLoading) return;
    
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    
    if (!canViewEmployees) {
      router.push('/my-claims');
      return;
    }

    fetchEmployees();
    fetchDropdowns();
  }, [roleFilter, includeInactive, isLoading, isAuthenticated, canViewEmployees, router]);

  async function fetchEmployees() {
    try {
      setLoading(true);
      let url = `${API_BASE_URL}/api/employees?include_inactive=${includeInactive}`;
      if (roleFilter) url += `&role=${roleFilter}`;
      
      const res = await authenticatedFetch(url);
      if (!res.ok) throw new Error('Failed to fetch employees');
      
      const data = await res.json();
      setEmployees(data.employees || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load employees');
    } finally {
      setLoading(false);
    }
  }

  async function fetchDropdowns() {
    try {
      const [gradesRes, locationsRes, unitsRes, rolesRes] = await Promise.all([
        authenticatedFetch(`${API_BASE_URL}/api/grades`),
        authenticatedFetch(`${API_BASE_URL}/api/locations`),
        authenticatedFetch(`${API_BASE_URL}/api/units`),
        authenticatedFetch(`${API_BASE_URL}/api/roles`),
      ]);
      
      if (gradesRes.ok) {
        const data = await gradesRes.json();
        setGrades(data.grades || []);
      }
      if (locationsRes.ok) {
        const data = await locationsRes.json();
        setLocations(data.locations || []);
      }
      if (unitsRes.ok) {
        const data = await unitsRes.json();
        setUnits(data.units || []);
      }
      if (rolesRes.ok) {
        const data = await rolesRes.json();
        // API returns array directly, not { roles: [...] }
        setRoles(Array.isArray(data) ? data : (data.roles || []));
      }
    } catch (err) {
      console.error('Error fetching dropdowns:', err);
    }
  }

  function openAddModal() {
    setEditingEmployee(null);
    setFormData({
      employee_code: '',
      name: '',
      phone_number: '',
      email: '',
      grade_id: '',
      location_id: '',
      unit_id: '',
      manager_id: '',
      role: 'employee',
      spending_limit: '',
      spending_limit_period: 'monthly',
      spending_limit_custom_days: '',
    });
    setShowModal(true);
  }

  function openEditModal(employee: Employee) {
    setEditingEmployee(employee);
    setFormData({
      employee_code: employee.employee_code,
      name: employee.name,
      phone_number: employee.phone_number,
      email: employee.email || '',
      grade_id: employee.grade_id?.toString() || '',
      location_id: employee.location_id?.toString() || '',
      unit_id: employee.unit_id?.toString() || '',
      manager_id: employee.manager_id?.toString() || '',
      role: employee.role,
      spending_limit: employee.spending_limit?.toString() || '',
      spending_limit_period: employee.spending_limit_period || 'monthly',
      spending_limit_custom_days: employee.spending_limit_custom_days?.toString() || '',
    });
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setProcessing(true);

    try {
      const payload = {
        ...formData,
        grade_id: formData.grade_id ? parseInt(formData.grade_id) : null,
        location_id: formData.location_id ? parseInt(formData.location_id) : null,
        unit_id: formData.unit_id ? parseInt(formData.unit_id) : null,
        manager_id: formData.manager_id ? parseInt(formData.manager_id) : null,
        spending_limit: formData.spending_limit ? parseFloat(formData.spending_limit) : null,
        spending_limit_period: formData.spending_limit || formData.spending_limit !== '' ? formData.spending_limit_period : 'monthly',
        spending_limit_custom_days: formData.spending_limit_custom_days ? parseInt(formData.spending_limit_custom_days) : null,
      };

      const url = editingEmployee 
        ? `${API_BASE_URL}/api/employees/${editingEmployee.id}`
        : `${API_BASE_URL}/api/employees`;
      
      const res = await authenticatedFetch(url, {
        method: editingEmployee ? 'PUT' : 'POST',
        headers: { 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to save employee');
      }

      setShowModal(false);
      fetchEmployees();
      alert(editingEmployee ? '✅ Employee updated!' : '✅ Employee created!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save employee');
    } finally {
      setProcessing(false);
    }
  }

  async function handleDelete(employee: Employee) {
    if (!confirm(`Are you sure you want to permanently delete ${employee.name}? This action cannot be undone.`)) return;
    
    try {
      // Use permanent=true to delete from database instead of soft delete
      const res = await authenticatedFetch(`${API_BASE_URL}/api/employees/${employee.id}?permanent=true`, {
        method: 'DELETE',
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to delete');
      }
      
      fetchEmployees();
      alert('✅ Employee permanently deleted');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete');
    }
  }

  const filteredEmployees = employees.filter(e => 
    e.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.employee_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.phone_number.includes(searchTerm)
  );

  // Paginate filtered employees
  const totalEmployees = filteredEmployees.length;
  const totalPages = Math.ceil(totalEmployees / itemsPerPage);
  const paginatedEmployees = filteredEmployees.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const managers = employees.filter(e => e.role === 'manager' || e.role === 'admin');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Employee Management</h2>
          <p className="text-gray-900">{totalEmployees} employees</p>
        </div>
        <button
          onClick={openAddModal}
          className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
        >
          + Add Employee
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 bg-white rounded-xl shadow-md p-4">
        <input
          type="text"
          placeholder="Search by name, code, or phone..."
          value={searchTerm}
          onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
          className="flex-1 min-w-[200px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
        />
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setCurrentPage(1); }}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Roles</option>
          <option value="employee">Staff</option>
          <option value="manager">Manager</option>
          <option value="admin">Admin</option>
        </select>
        <label className="flex items-center gap-2 text-gray-900">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="rounded"
          />
          Show Inactive
        </label>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        /* Employees Table */
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Code</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Phone</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Grade</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Location</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Spending Limit</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-900 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {paginatedEmployees.map((employee) => (
                <tr key={employee.id} className={`hover:bg-gray-50 ${!employee.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 font-mono text-sm">{employee.employee_code}</td>
                  <td className="px-4 py-3 font-medium">{employee.name}</td>
                  <td className="px-4 py-3 text-gray-900">{employee.phone_number}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      employee.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                      employee.role === 'manager' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {employee.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-900">{employee.grade_code || '-'}</td>
                  <td className="px-4 py-3 text-gray-900">{employee.location_name || '-'}</td>
                  <td className="px-4 py-3 text-gray-900 text-sm">
                    {employee.spending_limit != null ? (
                      <span>
                        <span className="font-medium">Rs {Number(employee.spending_limit).toLocaleString()}</span>
                        <span className="text-gray-500 text-xs block">
                          / {employee.spending_limit_period === 'custom' && employee.spending_limit_custom_days
                              ? `${employee.spending_limit_custom_days} days`
                              : employee.spending_limit_period || 'month'}
                        </span>
                      </span>
                    ) : (
                      <span className="text-gray-400 italic">Unlimited</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      employee.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {employee.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => openEditModal(employee)}
                          className="px-2 py-1 text-sm text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded transition-colors"
                        >
                          Edit
                        </button>
                        {employee.is_active && (
                          <button
                            onClick={() => handleDelete(employee)}
                            className="px-2 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                          >
                            Delete
                          </button>
                        )}
                        <button
                          onClick={() => router.push(`/claims?employee_id=${employee.id}`)}
                          className="px-2 py-1 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
                        >
                          Claims
                        </button>
                      </div>
                  </td>
                </tr>
              ))}
              {paginatedEmployees.length === 0 && (
                <tr>
                   <td colSpan={9} className="px-4 py-8 text-center text-gray-900">
                    No employees found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          
          {/* Pagination Controls */}
          {totalEmployees > 0 && (
            <div className="px-4 py-4 bg-gray-50 border-t flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-700">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, totalEmployees)} of {totalEmployees} employees
                </span>
                <select
                  value={itemsPerPage}
                  onChange={(e) => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value={5}>5 per page</option>
                  <option value={10}>10 per page</option>
                  <option value={25}>25 per page</option>
                  <option value={50}>50 per page</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 bg-white border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ← Previous
                </button>
                <span className="px-3 py-1 text-sm">
                  Page {currentPage} of {totalPages || 1}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1 bg-white border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">
                {editingEmployee ? 'Edit Employee' : 'Add New Employee'}
              </h3>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    {editingEmployee ? (
                      <>
                        <label className="block text-sm font-medium text-gray-900 mb-1">
                          Employee Code
                        </label>
                        <input
                          type="text"
                          value={formData.employee_code}
                          onChange={(e) => setFormData({...formData, employee_code: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                        />
                      </>
                    ) : (
                      <>
                        <label className="block text-sm font-medium text-gray-900 mb-1">
                          Employee Code
                        </label>
                        <div className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-900 text-sm">
                          Auto-generated
                        </div>
                      </>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1">
                      Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1">
                      Phone Number *
                    </label>
                    <input
                      type="tel"
                      value={formData.phone_number}
                      onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
                      required
                      placeholder="94771234567"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white placeholder-gray-400"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1">
                      Role *
                    </label>
                    <select
                      value={formData.role}
                      onChange={(e) => setFormData({...formData, role: e.target.value})}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                    >
                      <option value="">Select Role</option>
                      {roles.map((role) => (
                        <option key={role.id} value={role.code}>{role.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1">
                      Grade
                    </label>
                    <select
                      value={formData.grade_id}
                      onChange={(e) => setFormData({...formData, grade_id: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                    >
                      <option value="">Select Grade</option>
                      {grades.map((g) => (
                        <option key={g.id} value={g.id}>{g.code} - {g.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1">
                      Location
                    </label>
                    <select
                      value={formData.location_id}
                      onChange={(e) => setFormData({...formData, location_id: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                    >
                      <option value="">Select Location</option>
                      {locations.map((l) => (
                        <option key={l.id} value={l.id}>{l.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1">
                      Unit
                    </label>
                    <select
                      value={formData.unit_id}
                      onChange={(e) => setFormData({...formData, unit_id: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                    >
                      <option value="">Select Unit</option>
                      {units.map((u) => (
                        <option key={u.id} value={u.id}>{u.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Manager
                  </label>
                  <select
                    value={formData.manager_id}
                    onChange={(e) => setFormData({...formData, manager_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                  >
                    <option value="">No Manager</option>
                    {managers.filter(m => m.id !== editingEmployee?.id).map((m) => (
                      <option key={m.id} value={m.id}>{m.name} ({m.role})</option>
                    ))}
                  </select>
                </div>

                {/* Spending Limit Section */}
                <div className="border-t pt-4 mt-2">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">💰 Spending Limit</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-900 mb-1">
                        Limit Amount
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.spending_limit}
                        onChange={(e) => setFormData({...formData, spending_limit: e.target.value})}
                        placeholder="Leave empty for unlimited"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white placeholder-gray-400"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-900 mb-1">
                        Period
                      </label>
                      <select
                        value={formData.spending_limit_period}
                        onChange={(e) => setFormData({...formData, spending_limit_period: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                      >
                        <option value="daily">Daily (1 Day)</option>
                        <option value="weekly">Weekly (7 Days)</option>
                        <option value="monthly">Monthly</option>
                        <option value="custom">Custom Days</option>
                      </select>
                    </div>
                  </div>
                  {formData.spending_limit_period === 'custom' && (
                    <div className="mt-3">
                      <label className="block text-sm font-medium text-gray-900 mb-1">
                        Custom Period (Days)
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={formData.spending_limit_custom_days}
                        onChange={(e) => setFormData({...formData, spending_limit_custom_days: e.target.value})}
                        placeholder="e.g. 14"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white placeholder-gray-400"
                      />
                    </div>
                  )}
                </div>

                <div className="flex gap-4 pt-4">
                  <button
                    type="submit"
                    disabled={processing}
                    className="flex-1 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {processing ? 'Saving...' : (editingEmployee ? 'Update' : 'Create')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 py-2 bg-gray-200 text-gray-900 font-medium rounded-lg hover:bg-gray-300 transition-colors"
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
