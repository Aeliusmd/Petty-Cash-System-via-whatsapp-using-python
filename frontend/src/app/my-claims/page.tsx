'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import UnifiedClaimModal from '@/components/UnifiedClaimModal';
import ClaimDetailsModal from '@/components/ClaimDetailsModal';
import { authenticatedFetch } from '@/utils/api';

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

// Helper functions (defined once)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

function formatCurrency(amount: number | null): string {
  if (amount === null || amount === undefined) return 'Rs.0';
  return `Rs.${amount.toLocaleString()}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-LK', {
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

function MyClaimsContent() {
  const router = useRouter();
  const { user, isAuthenticated, logout, isLoading } = useAuth();
  
  const [claims, setClaims] = useState<Claim[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeStatus, setActiveStatus] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [showNewClaimModal, setShowNewClaimModal] = useState(false);
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router, isLoading]);

  useEffect(() => {
    if (isLoading) return;
    if (user) {
      fetchClaims();
      
      // Auto-refresh every 10 seconds (silent refresh)
      const interval = setInterval(() => {
        fetchClaims(true); // true = silent refresh, no loading state
      }, 10000);
      
      return () => clearInterval(interval);
    }
  }, [user, activeStatus, currentPage, isLoading]);

  async function fetchClaims(silent = false) {
    if (!user) return;
    
    // Only show loading state if not a silent background refresh
    if (!silent) {
      setLoading(true);
    }
    try {
      const params = new URLSearchParams();
      params.set('employee_id', user.id.toString());
      if (activeStatus) {
        params.set('status', activeStatus);
      }
      params.set('limit', itemsPerPage.toString());
      params.set('offset', ((currentPage - 1) * itemsPerPage).toString());
      
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

  const statuses = ['', 'PENDING', 'APPEALED', 'APPROVED', 'REJECTED'];

  if (!isAuthenticated || !user) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header with User Info */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">My Claims</h2>
          <p className="text-gray-600">
            Welcome, {user.name} ({user.employee_code})
          </p>
          <p className="text-sm text-gray-500">{total} total claims • Auto-refreshes every 10s</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowNewClaimModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all font-medium shadow-lg"
          >
            + New Claim
          </button>
          <button
            onClick={logout}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Unified Claim Modal */}
      <UnifiedClaimModal
        isOpen={showNewClaimModal}
        onClose={() => setShowNewClaimModal(false)}
        onSuccess={() => fetchClaims()}
      />

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
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Category</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Amount</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Status</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-900 uppercase">Date</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-gray-900 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {claims.map((claim) => (
                  <tr key={claim.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <span className="font-medium text-indigo-600">
                        {claim.claim_number}
                      </span>
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
                        {claim.status_name}
                      </span>
                      {claim.status_code === 'REJECTED' && claim.rejection_reason && (
                        <p className="text-sm text-red-600 mt-1">Reason: {claim.rejection_reason}</p>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {formatDate(claim.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => setSelectedClaim(claim)}
                        className="text-indigo-600 hover:text-indigo-900 font-medium text-sm"
                      >
                        View Details
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
              <span className="text-sm text-gray-700">
                Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, total)} of {total} claims
              </span>
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

          {/* Claim Details Modal */}
          {selectedClaim && (
            <ClaimDetailsModal
              claim={selectedClaim}
              isOpen={!!selectedClaim}
              onClose={() => setSelectedClaim(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default function MyClaimsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    }>
      <MyClaimsContent />
    </Suspense>
  );
}
