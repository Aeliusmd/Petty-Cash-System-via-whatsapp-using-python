'use client';

import { useEffect, useState } from 'react';
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
  approval_policy_id: number | null;
  manager_name: string | null;
  spending_limit: number | null;
  spending_limit_period: string | null;
  spending_limit_custom_days: number | null;
}

interface Grade    { id: number; code: string; name: string; }
interface Location { id: number; code: string; name: string; }
interface Unit     { id: number; code: string; name: string; }
interface Role     { id: number; code: string; name: string; }
interface ApprovalPolicyOption { id: number; name: string; unit_id: number; }

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

const roleBadge = (role: string) => {
  const map: Record<string, string> = {
    admin:    'bg-purple-100 text-purple-800',
    manager:  'bg-blue-100 text-blue-800',
    employee: 'bg-gray-100 text-gray-700',
  };
  return map[role] ?? 'bg-gray-100 text-gray-700';
};

export default function EmployeesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, hasPermission } = useAuth();

  const [employees, setEmployees]       = useState<Employee[]>([]);
  const [grades, setGrades]             = useState<Grade[]>([]);
  const [locations, setLocations]       = useState<Location[]>([]);
  const [units, setUnits]               = useState<Unit[]>([]);
  const [roles, setRoles]               = useState<Role[]>([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [showModal, setShowModal]       = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [processing, setProcessing]     = useState(false);
  const [searchTerm, setSearchTerm]     = useState('');
  const [roleFilter, setRoleFilter]     = useState('');
  const [includeInactive, setIncludeInactive] = useState(false);
  const [approvalPolicyOptions, setApprovalPolicyOptions] = useState<ApprovalPolicyOption[]>([]);

  // Pagination
  const [currentPage, setCurrentPage]   = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Form
  const [formData, setFormData] = useState({
    employee_code: '',
    name: '',
    phone_number: '',
    email: '',
    grade_id: '',
    location_id: '',
    unit_id: '',
    manager_id: '',
    approval_policy_id: '',
    role: 'employee',
    spending_limit: '',
    spending_limit_period: 'monthly',
    spending_limit_custom_days: '',
  });

  const canViewEmployees   = hasPermission('employees.read.all');
  const canManageEmployees = hasPermission('employees.create') || hasPermission('employees.update');

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) { router.push('/login'); return; }
    if (!canViewEmployees) { router.push('/my-claims'); return; }
    fetchEmployees();
    fetchDropdowns();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFilter, includeInactive, isLoading, isAuthenticated, canViewEmployees]);

  async function fetchEmployees() {
    try {
      setLoading(true);
      let url = `${API_BASE_URL}/api/employees?include_inactive=${includeInactive}`;
      if (roleFilter) url += `&role=${roleFilter}`;
      const res = await authenticatedFetch(url, { cache: 'no-store' });
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
      const [gr, lo, un, ro] = await Promise.all([
        authenticatedFetch(`${API_BASE_URL}/api/grades`, { cache: 'no-store' }),
        authenticatedFetch(`${API_BASE_URL}/api/locations`, { cache: 'no-store' }),
        authenticatedFetch(`${API_BASE_URL}/api/units`, { cache: 'no-store' }),
        authenticatedFetch(`${API_BASE_URL}/api/roles`, { cache: 'no-store' }),
      ]);
      if (gr.ok) { const d = await gr.json(); setGrades(d.grades || []); }
      if (lo.ok) { const d = await lo.json(); setLocations(d.locations || []); }
      if (un.ok) { const d = await un.json(); setUnits(d.units || []); }
      if (ro.ok) { const d = await ro.json(); setRoles(Array.isArray(d) ? d : (d.roles || [])); }
    } catch (err) { console.error('Dropdown fetch error:', err); }
  }

  function openAddModal() {
    setEditingEmployee(null);
    setFormData({ employee_code: '', name: '', phone_number: '', email: '', grade_id: '', location_id: '', unit_id: '', manager_id: '', approval_policy_id: '', role: 'employee', spending_limit: '', spending_limit_period: 'monthly', spending_limit_custom_days: '' });
    setApprovalPolicyOptions([]);
    setShowModal(true);
  }

  function openEditModal(emp: Employee) {
    setEditingEmployee(emp);
    setFormData({
      employee_code: emp.employee_code,
      name: emp.name,
      phone_number: emp.phone_number,
      email: emp.email || '',
      grade_id: emp.grade_id?.toString() || '',
      location_id: emp.location_id?.toString() || '',
      unit_id: emp.unit_id?.toString() || '',
      manager_id: emp.manager_id?.toString() || '',
      approval_policy_id: emp.approval_policy_id?.toString() || '',
      role: emp.role,
      spending_limit: emp.spending_limit?.toString() || '',
      spending_limit_period: emp.spending_limit_period || 'monthly',
      spending_limit_custom_days: emp.spending_limit_custom_days?.toString() || '',
    });
    if (emp.unit_id) {
      fetchApprovalPolicies(emp.unit_id);
    } else {
      setApprovalPolicyOptions([]);
    }
    setShowModal(true);
  }

  async function fetchApprovalPolicies(unitId: number) {
    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/approval-policies?unit_id=${unitId}`);
      if (!res.ok) {
        setApprovalPolicyOptions([]);
        return;
      }
      const data = await res.json();
      const policies = (data.policies || []).map((p: any) => ({ id: p.id, name: p.name, unit_id: p.unit_id }));
      setApprovalPolicyOptions(policies);
    } catch (error) {
      console.error('Failed to fetch approval policies', error);
      setApprovalPolicyOptions([]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setProcessing(true);
    try {
      const payload = {
        ...formData,
        grade_id:    formData.grade_id    ? parseInt(formData.grade_id)    : null,
        location_id: formData.location_id ? parseInt(formData.location_id) : null,
        unit_id:     formData.unit_id     ? parseInt(formData.unit_id)     : null,
        manager_id:  formData.manager_id  ? parseInt(formData.manager_id)  : null,
        approval_policy_id: formData.approval_policy_id ? parseInt(formData.approval_policy_id) : null,
        spending_limit: formData.spending_limit ? parseFloat(formData.spending_limit) : null,
        spending_limit_period: formData.spending_limit_period,
        spending_limit_custom_days: formData.spending_limit_custom_days ? parseInt(formData.spending_limit_custom_days) : null,
      };
      const url = editingEmployee
        ? `${API_BASE_URL}/api/employees/${editingEmployee.id}`
        : `${API_BASE_URL}/api/employees`;
      const res = await authenticatedFetch(url, {
        method: editingEmployee ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Failed to save'); }
      setShowModal(false);
      fetchEmployees();
      alert(editingEmployee ? '✅ Employee updated!' : '✅ Employee created!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save employee');
    } finally {
      setProcessing(false);
    }
  }

  async function handleDelete(emp: Employee) {
    if (!confirm(`Permanently delete ${emp.name}? This cannot be undone.`)) return;
    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/employees/${emp.id}?permanent=true`, { method: 'DELETE' });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Failed to delete'); }
      fetchEmployees();
      alert('✅ Employee permanently deleted');
    } catch (err) { alert(err instanceof Error ? err.message : 'Failed to delete'); }
  }

  const filteredEmployees = employees.filter(e =>
    e.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.employee_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.phone_number.includes(searchTerm)
  );

  const totalEmployees   = filteredEmployees.length;
  const totalPages       = Math.ceil(totalEmployees / itemsPerPage);
  const paginatedEmployees = filteredEmployees.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );
  const managers = employees.filter(e => e.role === 'manager' || e.role === 'admin');

  const spendingLimitLabel = (emp: Employee) => {
    if (emp.spending_limit == null) return 'Unlimited';
    const period = emp.spending_limit_period === 'custom' && emp.spending_limit_custom_days
      ? `${emp.spending_limit_custom_days}d`
      : emp.spending_limit_period ?? 'month';
    return `Rs ${Number(emp.spending_limit).toLocaleString()} / ${period}`;
  };

  const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white';

  return (
    <div className="space-y-4">

      {/* ── Header ── */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-gray-800">Employee Management</h2>
          <p className="text-sm text-gray-500">{totalEmployees} employees</p>
        </div>
        {canManageEmployees && (
          <button
            onClick={openAddModal}
            className="shrink-0 px-3 py-2 md:px-4 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            + Add Employee
          </button>
        )}
      </div>

      {/* ── Filters ── */}
      <div className="bg-white rounded-xl shadow-sm p-3 md:p-4 flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          placeholder="Search name, code, phone…"
          value={searchTerm}
          onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1); }}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-sm"
        />
        <select
          value={roleFilter}
          onChange={e => { setRoleFilter(e.target.value); setCurrentPage(1); }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Roles</option>
          <option value="employee">Staff</option>
          <option value="manager">Manager</option>
          <option value="admin">Admin</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-700 whitespace-nowrap">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={e => setIncludeInactive(e.target.checked)}
            className="rounded"
          />
          Show Inactive
        </label>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm">{error}</div>
      )}

      {/* ── Content ── */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <>
          {/* ── MOBILE CARDS (hidden on md+) ── */}
          <div className="md:hidden space-y-3">
            {paginatedEmployees.length === 0 ? (
              <div className="text-center py-12 text-gray-400">No employees found</div>
            ) : paginatedEmployees.map(emp => (
              <div
                key={emp.id}
                className={`bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-3 ${!emp.is_active ? 'opacity-60' : ''}`}
              >
                {/* Top row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate">{emp.name}</p>
                    <p className="text-xs font-mono text-gray-500">{emp.employee_code}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${roleBadge(emp.role)}`}>
                      {emp.role}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${emp.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {emp.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>

                {/* Detail rows */}
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <div>
                    <span className="text-xs text-gray-400 block">Phone</span>
                    <span className="text-gray-800">{emp.phone_number}</span>
                  </div>
                  {emp.grade_code && (
                    <div>
                      <span className="text-xs text-gray-400 block">Grade</span>
                      <span className="text-gray-800">{emp.grade_code}</span>
                    </div>
                  )}
                  {emp.location_name && (
                    <div>
                      <span className="text-xs text-gray-400 block">Location</span>
                      <span className="text-gray-800">{emp.location_name}</span>
                    </div>
                  )}
                  {emp.unit_name && (
                    <div>
                      <span className="text-xs text-gray-400 block">Unit</span>
                      <span className="text-gray-800">{emp.unit_name}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-xs text-gray-400 block">Spending Limit</span>
                    <span className="text-gray-800">{spendingLimitLabel(emp)}</span>
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex gap-2 pt-2 border-t border-gray-50">
                  {canManageEmployees && (
                    <button
                      onClick={() => openEditModal(emp)}
                      className="flex-1 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors font-medium"
                    >
                      ✏️ Edit
                    </button>
                  )}
                  <button
                    onClick={() => router.push(`/claims?employee_id=${emp.id}`)}
                    className="flex-1 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors font-medium"
                  >
                    📋 Claims
                  </button>
                  {canManageEmployees && emp.is_active && (
                    <button
                      onClick={() => handleDelete(emp)}
                      className="flex-1 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors font-medium"
                    >
                      🗑️ Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* ── DESKTOP TABLE (hidden on mobile) ── */}
          <div className="hidden md:block bg-white rounded-xl shadow-md overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    {['Code','Name','Phone','Role','Grade','Location','Spending Limit','Status','Actions'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {paginatedEmployees.map(emp => (
                    <tr key={emp.id} className={`hover:bg-gray-50 transition-colors ${!emp.is_active ? 'opacity-50' : ''}`}>
                      <td className="px-4 py-3 font-mono text-sm text-gray-700">{emp.employee_code}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{emp.name}</td>
                      <td className="px-4 py-3 text-gray-700 text-sm">{emp.phone_number}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${roleBadge(emp.role)}`}>{emp.role}</span>
                      </td>
                      <td className="px-4 py-3 text-gray-700 text-sm">{emp.grade_code || '–'}</td>
                      <td className="px-4 py-3 text-gray-700 text-sm">{emp.location_name || '–'}</td>
                      <td className="px-4 py-3 text-sm">
                        {emp.spending_limit != null ? (
                          <span>
                            <span className="font-medium text-gray-800">Rs {Number(emp.spending_limit).toLocaleString()}</span>
                            <span className="text-gray-400 text-xs block">
                              / {emp.spending_limit_period === 'custom' && emp.spending_limit_custom_days
                                   ? `${emp.spending_limit_custom_days}d`
                                   : emp.spending_limit_period ?? 'month'}
                            </span>
                          </span>
                        ) : <span className="text-gray-400 italic text-xs">Unlimited</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${emp.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {emp.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1.5 flex-wrap">
                          {canManageEmployees && (
                            <button onClick={() => openEditModal(emp)} className="px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-50 rounded transition-colors">Edit</button>
                          )}
                          <button onClick={() => router.push(`/claims?employee_id=${emp.id}`)} className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded transition-colors">Claims</button>
                          {canManageEmployees && emp.is_active && (
                            <button onClick={() => handleDelete(emp)} className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors">Delete</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {paginatedEmployees.length === 0 && (
                    <tr>
                      <td colSpan={9} className="px-4 py-10 text-center text-gray-400">No employees found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Pagination ── */}
          {totalEmployees > 0 && (
            <div className="bg-white rounded-xl shadow-sm px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <span>
                  {((currentPage - 1) * itemsPerPage) + 1}–{Math.min(currentPage * itemsPerPage, totalEmployees)} of {totalEmployees}
                </span>
                <select
                  value={itemsPerPage}
                  onChange={e => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm"
                >
                  {[5,10,25,50].map(n => <option key={n} value={n}>{n} / page</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1.5 bg-white border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ← Prev
                </button>
                <span className="px-2 text-sm text-gray-600">{currentPage} / {totalPages || 1}</span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1.5 bg-white border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Modal ── */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
          <div className="bg-white w-full sm:rounded-xl shadow-xl sm:max-w-lg max-h-[92dvh] overflow-y-auto rounded-t-2xl">
            <div className="p-4 md:p-6">
              {/* Modal header */}
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-semibold text-gray-900">
                  {editingEmployee ? 'Edit Employee' : 'Add New Employee'}
                </h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                >
                  ×
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Code + Name */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Employee Code</label>
                    {editingEmployee ? (
                      <input type="text" value={formData.employee_code} onChange={e => setFormData({...formData, employee_code: e.target.value})} className={inputCls} />
                    ) : (
                      <div className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-400 text-sm">Auto-generated</div>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                    <input type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required className={inputCls} />
                  </div>
                </div>

                {/* Phone + Email */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Phone *</label>
                    <input type="tel" value={formData.phone_number} onChange={e => setFormData({...formData, phone_number: e.target.value})} required placeholder="94771234567" className={inputCls} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className={inputCls} />
                  </div>
                </div>

                {/* Role + Grade */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Role *</label>
                    <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} required className={inputCls}>
                      <option value="">Select Role</option>
                      {roles.map(r => <option key={r.id} value={r.code}>{r.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Grade</label>
                    <select value={formData.grade_id} onChange={e => setFormData({...formData, grade_id: e.target.value})} className={inputCls}>
                      <option value="">Select Grade</option>
                      {grades.map(g => <option key={g.id} value={g.id}>{g.code} – {g.name}</option>)}
                    </select>
                  </div>
                </div>

                {/* Location + Unit */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                    <select value={formData.location_id} onChange={e => setFormData({...formData, location_id: e.target.value})} className={inputCls}>
                      <option value="">Select Location</option>
                      {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
                    <select value={formData.unit_id} onChange={e => {
                      const unit_id = e.target.value;
                      setFormData({...formData, unit_id, approval_policy_id: ''});
                      if (unit_id) {
                        fetchApprovalPolicies(parseInt(unit_id));
                      } else {
                        setApprovalPolicyOptions([]);
                      }
                    }} className={inputCls}>
                      <option value="">Select Unit</option>
                      {units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                    </select>
                  </div>
                </div>

                {/* Manager */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Manager</label>
                  <select value={formData.manager_id} onChange={e => setFormData({...formData, manager_id: e.target.value})} className={inputCls}>
                    <option value="">No Manager</option>
                    {managers.filter(m => m.id !== editingEmployee?.id).map(m => (
                      <option key={m.id} value={m.id}>{m.name} ({m.role})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Approval Policy</label>
                  <select value={formData.approval_policy_id} onChange={e => setFormData({...formData, approval_policy_id: e.target.value})} className={inputCls}>
                    <option value="">Use department default</option>
                    {approvalPolicyOptions.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

                {/* Spending Limit */}
                <div className="border-t pt-4 space-y-3">
                  <h4 className="text-sm font-semibold text-gray-700">💰 Spending Limit</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Limit Amount</label>
                      <input type="number" step="0.01" min="0" value={formData.spending_limit} onChange={e => setFormData({...formData, spending_limit: e.target.value})} placeholder="Leave empty for unlimited" className={inputCls} />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Period</label>
                      <select value={formData.spending_limit_period} onChange={e => setFormData({...formData, spending_limit_period: e.target.value})} className={inputCls}>
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                        <option value="custom">Custom Days</option>
                      </select>
                    </div>
                  </div>
                  {formData.spending_limit_period === 'custom' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Custom Days</label>
                      <input type="number" min="1" value={formData.spending_limit_custom_days} onChange={e => setFormData({...formData, spending_limit_custom_days: e.target.value})} placeholder="e.g. 14" className={inputCls} />
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <button type="submit" disabled={processing} className="flex-1 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                    {processing ? 'Saving…' : editingEmployee ? 'Update' : 'Create'}
                  </button>
                  <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 transition-colors">
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
