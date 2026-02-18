'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import ClaimDetailsModal from '@/components/ClaimDetailsModal';
import UnifiedClaimModal from '@/components/UnifiedClaimModal';
import ExportClaimsModal from '@/components/ExportClaimsModal';
import ClaimsList from '@/components/ClaimsList';
import { useAuth } from '@/contexts/AuthContext';
import { authenticatedFetch } from '@/utils/api';

interface Claim {
  id: number;
  claim_number: string;
  employee_id: number;
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
  const { isAuthenticated, isLoading, hasAnyPermission, user } = useAuth();
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get('status') || '';
  
  const [claims, setClaims] = useState<Claim[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const paramEmployeeId = searchParams.get('employee_id');
  const [activeStatus, setActiveStatus] = useState(statusFilter);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>(paramEmployeeId || '');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [processing, setProcessing] = useState<number | null>(null);
  
  // Modal state
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  
  // Warning Modal State
  const [showWarning, setShowWarning] = useState(false);
  const [warningClaim, setWarningClaim] = useState<Claim | null>(null);
  const [warningSummary, setWarningSummary] = useState<any>(null);
  const [processingApprove, setProcessingApprove] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Employee search autocomplete states
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Permission-based access
  const canViewAllClaims = hasAnyPermission(['claims.read.all', 'claims.read.team', 'claims.approve']);
  const canCreateClaim = hasAnyPermission(['claims.create']);

  // Modal state for new claim
  const [showNewClaimModal, setShowNewClaimModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);

  // Sync search text when employees load if filtering by URL param
  useEffect(() => {
    if (selectedEmployeeId && employees.length > 0 && !employeeSearch) {
      const emp = employees.find(e => e.id.toString() === selectedEmployeeId);
      if (emp) {
        setEmployeeSearch(`${emp.name} (${emp.employee_code})`);
      }
    }
  }, [selectedEmployeeId, employees]);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    // Check permission for this page
    if (!canViewAllClaims) {
        router.push('/my-claims');
        return;
    }
    
    fetchEmployees();
  }, [isLoading, isAuthenticated, canViewAllClaims, router]);


  useEffect(() => {
    fetchClaims();
    
    // Auto-refresh every 10 seconds (silent refresh)
    const interval = setInterval(() => {
      fetchClaims(true); // true = silent refresh, no loading state
    }, 10000);
    
    return () => clearInterval(interval);
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
      const res = await authenticatedFetch(`${API_BASE_URL}/api/employees?include_inactive=false`);
      if (!res.ok) throw new Error('Failed to fetch employees');
      const data = await res.json();
      setEmployees(data.employees || []);
    } catch (err) {
      console.error('Failed to load employees:', err);
    }
  }

  async function fetchClaims(silent = false) {
    // Only show loading state if not a silent background refresh
    if (!silent) {
      setLoading(true);
    }
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
      
      const res = await authenticatedFetch(`${API_BASE_URL}/api/claims?${params}`);
      if (!res.ok) throw new Error('Failed to fetch claims');
      const data = await res.json();
      setClaims(data.claims || []);
      setTotal(data.total || 0);
    } catch (err) {
      // Only set error on non-silent refresh to avoid disrupting user
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Failed to load claims');
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  async function handleApprove(claimId: number, finalAmount?: number, skipCheck = false) {
    // Find claim
    const claim = claims.find(c => c.id === claimId);
    if (!claim) return;

    // Phase 1: Check Spending Limit (unless skipped)
    if (!skipCheck && !finalAmount) {
      setProcessing(claimId);
      try {
        // Fetch spending summary
        const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/spending-summary/${claim.employee_id}`);
        if (res.ok) {
          const data = await res.json();
          const summary = data.data || data;
          
          if (summary.spending_limit) {
             const claimAmount = claim.final_amount || claim.system_amount || claim.user_amount || 0;
             const projectedTotal = (summary.total_spent || 0) + claimAmount;
             
             // If exceeds available (or limit), show warning
             // total_spent includes approved claims. This claim is pending, so add its amount.
             if (projectedTotal > summary.spending_limit) {
               setWarningClaim(claim);
               setWarningSummary(summary);
               setShowWarning(true);
               setProcessing(null);
               return; // Stop here, wait for modal interaction
             }
          }
        }
      } catch (err) {
        console.error('Failed to check spending limit:', err);
        // Continue to normal approve if check fails (fail open or closed? let's fail open but log)
      }
    }

    // Phase 2: Confirm & Execute
    if (!skipCheck && !confirm('Are you sure you want to approve this claim?')) {
      setProcessing(null);
      return;
    }
  
    setProcessing(claimId);
    try {
      const body = finalAmount ? { final_amount: finalAmount } : {};
      const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/${claimId}/approve`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to approve');
      }

      await fetchClaims(true); // Silent refresh
      
      // Close warning if open
      setShowWarning(false);
      setWarningClaim(null);
      setWarningSummary(null);
      
      alert('Claim approved! Staff has been notified via WhatsApp.');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to approve claim');
    } finally {
      setProcessing(null);
    }
  }

  async function handleReject(claimId: number, reason?: string) {
    const finalReason = reason || rejectReason;
    if (!finalReason.trim()) {
      alert('Please enter a rejection reason');
      return;
    }
    
    setProcessing(claimId);
    try {
      const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/${claimId}/reject`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({ reason: finalReason }),
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
      const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/${claimId}`, {
        method: 'DELETE',
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
        {/* New Claim Button - only visible with claims.create permission */}
        <div className="flex gap-2">
          <button
            onClick={() => setShowExportModal(true)}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-all font-medium shadow-sm flex items-center gap-2"
          >
            <span>📤</span> Export
          </button>
          
          {canCreateClaim && (
            <button
              onClick={() => setShowNewClaimModal(true)}
              className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all font-medium shadow-lg"
            >
              + New Claim
            </button>
          )}
        </div>
      </div>

      {/* Unified Claim Modal */}
      <UnifiedClaimModal
        isOpen={showNewClaimModal}
        onClose={() => setShowNewClaimModal(false)}
        onSuccess={() => fetchClaims()}
      />
      
      <ExportClaimsModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        organizationId={user?.organization_id}
      />

      {/* Filters Section */}
      <div className="flex flex-wrap gap-4">
        {/* Status Filter Tabs */}
        <div className="bg-white rounded-xl shadow-md p-2 flex overflow-x-auto w-full md:w-auto hide-scrollbar gap-2">
          {statuses.map((status) => (
            <button
              key={status || 'all'}
              onClick={() => { setActiveStatus(status); setCurrentPage(1); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex-shrink-0 ${
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
        <div className="bg-white rounded-xl shadow-md p-2 relative w-full md:w-auto">
          <div className="flex items-center gap-2">
            <div className="relative w-full">
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
                className="px-4 py-2 rounded-lg text-sm font-medium border-0 focus:ring-2 focus:ring-indigo-500 w-full md:w-64"
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

      {/* Claims List Component */}
      {!error && (
        <>
            <ClaimsList 
                claims={claims} 
                loading={loading} 
                processingId={processing}
                onView={(claim) => { setSelectedClaim(claim); setIsModalOpen(true); }}
                onApprove={handleApprove}
                onReject={(id, reason) => {
                    setRejectReason(reason); // syncing locally to pass to handleReject if needed, but handleReject reads from state. 
                    // Wait, handleReject reads from state `rejectReason`. 
                    // Prop onReject passes (id, reason). 
                    // We need to update handleReject to accept reason or update state before calling.
                    // Let's modify handleReject signature below first.
                    handleReject(id, reason);
                }}
                onDelete={handleDelete}
            />
          
          {/* Pagination Controls */}
          {!loading && claims.length > 0 && (
            <div className="px-6 py-4 bg-gray-50 border-t flex flex-col md:flex-row items-center justify-between rounded-b-xl border border-t-0 border-gray-200 mt-[-1px] gap-4 md:gap-0">
              <div className="flex flex-col md:flex-row items-center gap-4 text-center md:text-left">
                <span className="text-sm text-gray-700">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, total)} of {total} claims
                </span>
                <select
                  value={itemsPerPage}
                  onChange={(e) => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm w-full md:w-auto"
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
        </>
      )}
      
      {/* Claim Details Modal */}
      {selectedClaim && (
        <ClaimDetailsModal
          claim={selectedClaim}
          isOpen={isModalOpen}
          onClose={() => { setIsModalOpen(false); setSelectedClaim(null); }}
        />
      )}
      {/* Spending Limit Warning Modal */}
      {showWarning && warningClaim && warningSummary && (
        <div className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 animate-in fade-in zoom-in duration-200">
            <div className="flex items-start gap-4 mb-6">
              <div className="bg-yellow-100 p-3 rounded-full">
                <span className="text-2xl">⚠️</span>
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900">Spending Limit Exceeded</h3>
                <p className="text-gray-600 mt-1">
                  This claim exceeds the employee's available budget.
                </p>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 mb-6 space-y-3 text-sm">
               <div className="flex justify-between">
                 <span className="text-gray-600">Employee:</span>
                 <span className="font-medium text-gray-900">{warningClaim.employee_name}</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-600">Period ({warningSummary.period_label}):</span>
                 <span className="font-medium text-gray-900">
                   {formatCurrency(warningSummary.total_spent)} / {formatCurrency(warningSummary.spending_limit)}
                 </span>
               </div>
               <div className="flex justify-between border-t pt-2">
                 <span className="text-gray-800 font-semibold">Available Budget:</span>
                 <span className="font-bold text-green-600">{formatCurrency(warningSummary.available)}</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-800 font-semibold">Claim Amount:</span>
                 <span className="font-bold text-red-600">
                   {formatCurrency(warningClaim.final_amount || warningClaim.system_amount || warningClaim.user_amount)}
                 </span>
               </div>
            </div>

            <div className="flex flex-col gap-3">
              <button
                onClick={() => handleApprove(warningClaim.id, warningSummary.available, true)}
                disabled={processing === warningClaim.id}
                className="w-full py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
              >
                Approve {formatCurrency(warningSummary.available)} (Available)
              </button>
              
              <button
                onClick={() => handleApprove(warningClaim.id, undefined, true)}
                disabled={processing === warningClaim.id}
                className="w-full py-2.5 bg-white border-2 border-orange-200 text-orange-700 font-medium rounded-lg hover:bg-orange-50 transition-colors"
              >
                Approve Full Amount (Override)
              </button>
              
              <button
                onClick={() => {
                  setShowWarning(false);
                  setRejectReason('Budget limit exceeded');
                  setRejectingId(warningClaim.id);
                }}
                className="w-full py-2.5 text-red-600 font-medium hover:bg-red-50 rounded-lg transition-colors"
              >
                Reject Claim
              </button>
              
              <button
                onClick={() => setShowWarning(false)}
                className="w-full py-2 text-gray-500 hover:text-gray-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
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
