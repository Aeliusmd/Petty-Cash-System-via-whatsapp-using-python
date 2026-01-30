'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import ClaimDetailsModal from '@/components/ClaimDetailsModal';
import { useAuth } from '@/contexts/AuthContext';

interface Claim {
  id: number;
  claim_number: string;
  employee_name: string;
  employee_code: string;
  category_name: string;
  category_code: string;
  location_name: string | null;
  status_code: string;
  status_name: string;
  claim_type: string;
  claim_date: string;
  duration_days: number;
  user_amount: number | null;
  system_amount: number | null;
  final_amount: number | null;
  description: string | null;
  rejection_reason: string | null;
  appeal_count: number | null;
  created_at: string;
}

interface Employee {
  id: number;
  name: string;
  employee_code: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

function formatCurrency(amount: number | null): string {
  if (amount === null || amount === undefined) return 'Rs.0';
  return `Rs.${amount.toLocaleString()}`;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '-';
  
  return date.toLocaleDateString('en-LK', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'PENDING': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'APPROVED': return 'bg-green-100 text-green-800 border-green-200';
    case 'REJECTED': return 'bg-red-100 text-red-800 border-red-200';
    case 'APPEALED': return 'bg-purple-100 text-purple-800 border-purple-200';
    default: return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

function getCategoryIcon(code: string): string {
  switch (code) {
    case 'BATTA': return '🏷️';
    case 'FUEL': return '⛽';
    case 'ACCOM': return '🏨';
    case 'SUNDRY': return '📦';
    default: return '📋';
  }
}



function ClaimsContent() {
  const router = useRouter();
  const { isAuthenticated, isAdmin, isManager, isLoading } = useAuth();
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get('status') || '';
  
  const [claims, setClaims] = useState<Claim[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeStatus, setActiveStatus] = useState(statusFilter);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [processing, setProcessing] = useState<number | null>(null);
  
  // Modal state
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Employee search autocomplete states
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    // Optional: add role check if needed, though API will 403
    if (!isAdmin && !isManager) {
        router.push('/my-claims');
        return;
    }
    
    fetchEmployees();
  }, [isLoading, isAuthenticated, isAdmin, isManager, router]);


  useEffect(() => {
    fetchClaims();
  }, [activeStatus, selectedEmployeeId, currentPage, itemsPerPage]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setShowSuggestions(false);
    if (showSuggestions) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showSuggestions]);

  async function fetchEmployees() {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${API_BASE_URL}/api/employees?include_inactive=false`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch employees');
      const data = await res.json();
      setEmployees(data.employees || []);
    } catch (err) {
      console.error('Failed to load employees:', err);
    }
  }

  async function fetchClaims() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeStatus) {
        params.set('status', activeStatus);
      }
      if (selectedEmployeeId) {
        params.set('employee_id', selectedEmployeeId);
      }
      // Add pagination params
      params.set('limit', itemsPerPage.toString());
      params.set('offset', ((currentPage - 1) * itemsPerPage).toString());

      // Filter by manager if logged in as manager
      const userStr = localStorage.getItem('auth_user');
      const user = userStr ? JSON.parse(userStr) : null;
      if (user && user.role === 'manager' && user.id) {
        params.set('manager_id', user.id.toString());
      }
      
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${API_BASE_URL}/api/claims?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch claims');
      const data = await res.json();
      setClaims(data.claims || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load claims');
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(claimId: number) {
    if (!confirm('Are you sure you want to approve this claim?')) return;
    
    setProcessing(claimId);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}/approve`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json' 
        },
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to approve');
      }
      await fetchClaims();
      alert('Claim approved! Staff has been notified via WhatsApp.');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to approve claim');
    } finally {
      setProcessing(null);
    }
  }

  async function handleReject(claimId: number) {
    if (!rejectReason.trim()) {
      alert('Please enter a rejection reason');
      return;
    }
    
    setProcessing(claimId);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}/reject`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({ reason: rejectReason }),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to reject');
      }
      setRejectingId(null);
      setRejectReason('');
      await fetchClaims();
      alert('Claim rejected! Staff has been notified via WhatsApp with the reason.');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reject claim');
    } finally {
      setProcessing(null);
    }
  }

  async function handleDelete(claimId: number, claimNumber: string) {
    if (!confirm(`Are you sure you want to delete claim ${claimNumber}? This action cannot be undone.`)) return;
    
    setProcessing(claimId);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to delete');
      }
      await fetchClaims();
      alert('✅ Claim deleted successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete claim');
    } finally {
      setProcessing(null);
    }
  }

  const statuses = ['', 'PENDING', 'APPEALED', 'APPROVED', 'REJECTED'];

  // Filter employees based on search query
  const filteredEmployees = employees.filter(emp =>
    emp.name.toLowerCase().includes(employeeSearch.toLowerCase()) ||
    emp.employee_code.toLowerCase().includes(employeeSearch.toLowerCase())
  );

  // Get selected employee name for display
  const selectedEmployee = employees.find(emp => emp.id.toString() === selectedEmployeeId);

  // Handle employee selection from suggestions
  const handleSelectEmployee = (emp: Employee) => {
    setSelectedEmployeeId(emp.id.toString());
    setEmployeeSearch(`${emp.name} (${emp.employee_code})`);
    setShowSuggestions(false);
    setCurrentPage(1);
  };

  // Clear employee filter
  const handleClearEmployee = () => {
    setSelectedEmployeeId('');
    setEmployeeSearch('');
    setShowSuggestions(false);
    setCurrentPage(1);
  };

  // Get display name for status, showing "Appeal & Approved" for claims that went through appeal
  const getClaimStatusDisplay = (claim: Claim) => {
    if (claim.status_code === 'APPROVED' && claim.appeal_count && claim.appeal_count > 0) {
      return 'Appeal & Approved';
    }
    return claim.status_name;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Claims</h2>
          <p className="text-gray-900">{total} total claims</p>
        </div>
      </div>

      {/* Filters Section */}
      <div className="flex flex-wrap gap-4">
        {/* Status Filter Tabs */}
        <div className="bg-white rounded-xl shadow-md p-2 inline-flex gap-2">
          {statuses.map((status) => (
            <button
              key={status || 'all'}
              onClick={() => { setActiveStatus(status); setCurrentPage(1); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeStatus === status
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-900 hover:bg-gray-100'
              }`}
            >
              {status || 'All'}
            </button>
          ))}
        </div>

        {/* Employee Filter - Autocomplete Search */}
        <div className="bg-white rounded-xl shadow-md p-2 relative">
          <div className="flex items-center gap-2">
            <div className="relative">
              <input
                type="text"
                value={employeeSearch}
                onChange={(e) => {
                  setEmployeeSearch(e.target.value);
                  setShowSuggestions(true);
                  if (!e.target.value) {
                    setSelectedEmployeeId('');
                    setCurrentPage(1);
                  }
                }}
                onFocus={() => setShowSuggestions(true)}
                placeholder="🔍 Search employee..."
                className="px-4 py-2 rounded-lg text-sm font-medium border-0 focus:ring-2 focus:ring-indigo-500 w-64"
              />
              {selectedEmployeeId && (
                <button
                  onClick={handleClearEmployee}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  title="Clear filter"
                >
                  ✕
                </button>
              )}
              
              {/* Suggestions Dropdown */}
              {showSuggestions && employeeSearch && (
                <div className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto z-50">
                  {filteredEmployees.length > 0 ? (
                    filteredEmployees.map((emp) => (
                      <button
                        key={emp.id}
                        onClick={() => handleSelectEmployee(emp)}
                        className="w-full px-4 py-2 text-left hover:bg-indigo-50 flex items-center justify-between text-sm"
                      >
                        <span className="font-medium">{emp.name}</span>
                        <span className="text-gray-500 text-xs">{emp.employee_code}</span>
                      </button>
                    ))
                  ) : (
                    <div className="px-4 py-2 text-sm text-gray-500">No employees found</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
        </div>
      )}

      {/* Claims List */}
      {!loading && !error && (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          {claims.length === 0 ? (
            <div className="p-8 text-center text-gray-900">
              No claims found
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Claim #</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Employee</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Category</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Amount</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Status</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Date</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">View</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {claims.map((claim) => (
                  <tr key={claim.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <Link href={`/claims/${claim.id}`} className="font-medium text-indigo-600 hover:text-indigo-800">
                        {claim.claim_number}
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-800">{claim.employee_name}</p>
                      <p className="text-sm text-gray-900">{claim.employee_code}</p>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span>{getCategoryIcon(claim.category_code)}</span>
                        <span>{claim.category_name}</span>
                      </div>
                      {claim.location_name && (
                        <p className="text-sm text-gray-900">📍 {claim.location_name}</p>
                      )}
                    </td>
                    <td className="px-6 py-4 font-medium">
                      {formatCurrency(claim.final_amount || claim.system_amount || claim.user_amount)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(claim.status_code)}`}>
                        {getClaimStatusDisplay(claim)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {formatDate(claim.claim_date || claim.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => { setSelectedClaim(claim); setIsModalOpen(true); }}
                        className="text-indigo-600 hover:text-indigo-800 font-medium text-sm flex items-center gap-1"
                        title="View Details"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        View
                      </button>
                    </td>
                    <td className="px-6 py-4">
                      {(claim.status_code === 'PENDING' || claim.status_code === 'APPEALED') && rejectingId !== claim.id && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleApprove(claim.id)}
                            disabled={processing === claim.id}
                            className="px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                          >
                            {processing === claim.id ? '...' : '✓ Approve'}
                          </button>
                          <button
                            onClick={() => setRejectingId(claim.id)}
                            disabled={processing === claim.id}
                            className="px-3 py-1.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                          >
                            ✗ Reject
                          </button>
                        </div>
                      )}
                      {(claim.status_code === 'PENDING' || claim.status_code === 'APPEALED') && rejectingId === claim.id && (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            placeholder="Reason..."
                            className="w-32 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-red-500"
                            autoFocus
                          />
                          <button
                            onClick={() => handleReject(claim.id)}
                            disabled={processing === claim.id || !rejectReason.trim()}
                            className="px-2 py-1 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700 disabled:opacity-50"
                          >
                            {processing === claim.id ? '...' : 'Confirm'}
                          </button>
                          <button
                            onClick={() => { setRejectingId(null); setRejectReason(''); }}
                            className="px-2 py-1 bg-gray-200 text-gray-900 text-xs font-medium rounded hover:bg-gray-300"
                          >
                            ✕
                          </button>
                        </div>
                      )}
                      {claim.status_code === 'REJECTED' && claim.rejection_reason && (
                        <p className="text-sm text-red-600">Reason: {claim.rejection_reason}</p>
                      )}
                      {/* Delete Button - always visible */}
                      <button
                        onClick={() => handleDelete(claim.id, claim.claim_number)}
                        disabled={processing === claim.id}
                        className="mt-2 px-2 py-1 text-xs text-red-500 hover:text-red-700 hover:underline"
                      >
                        🗑️ Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          
          {/* Pagination Controls */}
          {claims.length > 0 && (
            <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-700">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, total)} of {total} claims
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
                  Page {currentPage} of {Math.ceil(total / itemsPerPage) || 1}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(Math.ceil(total / itemsPerPage), p + 1))}
                  disabled={currentPage >= Math.ceil(total / itemsPerPage)}
                  className="px-3 py-1 bg-white border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Claim Details Modal */}
      {selectedClaim && (
        <ClaimDetailsModal
          claim={selectedClaim}
          isOpen={isModalOpen}
          onClose={() => { setIsModalOpen(false); setSelectedClaim(null); }}
        />
      )}
    </div>
  );
}

export default function ClaimsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    }>
      <ClaimsContent />
    </Suspense>
  );
}
