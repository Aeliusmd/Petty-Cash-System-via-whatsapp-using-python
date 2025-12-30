'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

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
  created_at: string;
}

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

function ClaimsContent() {
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get('status') || '';
  
  const [claims, setClaims] = useState<Claim[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeStatus, setActiveStatus] = useState(statusFilter);

  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [processing, setProcessing] = useState<number | null>(null);

  useEffect(() => {
    fetchClaims();
  }, [activeStatus]);

  async function fetchClaims() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeStatus) params.set('status', activeStatus);
      
      const res = await fetch(`${API_BASE_URL}/api/claims?${params}`);
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
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  const statuses = ['', 'PENDING', 'APPEALED', 'APPROVED', 'REJECTED'];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Claims</h2>
          <p className="text-gray-500">{total} total claims</p>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="bg-white rounded-xl shadow-md p-2 inline-flex gap-2">
        {statuses.map((status) => (
          <button
            key={status || 'all'}
            onClick={() => setActiveStatus(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeStatus === status
                ? 'bg-indigo-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
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
            <div className="p-8 text-center text-gray-500">
              No claims found
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase">Claim #</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase">Employee</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
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
                      <p className="text-sm text-gray-500">{claim.employee_code}</p>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span>{getCategoryIcon(claim.category_code)}</span>
                        <span>{claim.category_name}</span>
                      </div>
                      {claim.location_name && (
                        <p className="text-sm text-gray-500">📍 {claim.location_name}</p>
                      )}
                    </td>
                    <td className="px-6 py-4 font-medium">
                      {formatCurrency(claim.final_amount || claim.system_amount || claim.user_amount)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(claim.status_code)}`}>
                        {claim.status_name}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDate(claim.created_at)}
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
                            className="px-2 py-1 bg-gray-200 text-gray-700 text-xs font-medium rounded hover:bg-gray-300"
                          >
                            ✕
                          </button>
                        </div>
                      )}
                      {claim.status_code === 'REJECTED' && claim.rejection_reason && (
                        <p className="text-sm text-red-600">Reason: {claim.rejection_reason}</p>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
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
