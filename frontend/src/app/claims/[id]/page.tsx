'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';

interface Claim {
  id: number;
  claim_number: string;
  employee_name: string;
  employee_code: string;
  phone_number?: string;
  grade_code: string;
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
  appeal_count?: number;
  manager_name: string | null;
  approver_name: string | null;
  created_at: string;
  approved_at: string | null;
}

interface HistoryItem {
  id: number;
  from_status_code: string | null;
  from_status_name: string | null;
  to_status_code: string;
  to_status_name: string;
  changed_by_name: string | null;
  reason: string | null;
  created_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

function formatCurrency(amount: number | null): string {
  if (amount === null || amount === undefined) return 'Rs.0';
  return `Rs.${amount.toLocaleString()}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-LK', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'PENDING': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case 'APPROVED': return 'bg-green-100 text-green-800 border-green-300';
    case 'REJECTED': return 'bg-red-100 text-red-800 border-red-300';
    case 'APPEALED': return 'bg-purple-100 text-purple-800 border-purple-300';
    default: return 'bg-gray-100 text-gray-800 border-gray-300';
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'PENDING': return '⏳';
    case 'APPROVED': return '✅';
    case 'REJECTED': return '❌';
    case 'APPEALED': return '🔄';
    case 'DRAFT': return '📝';
    case 'PAID': return '💵';
    default: return '📋';
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

export default function ClaimDetailPage() {
  const params = useParams();
  const router = useRouter();
  const claimId = params.id as string;

  const [claim, setClaim] = useState<Claim | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  useEffect(() => {
    fetchClaim();
    fetchHistory();
  }, [claimId]);

  async function fetchClaim() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}`);
      if (!res.ok) throw new Error('Claim not found');
      const data = await res.json();
      setClaim(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load claim');
    } finally {
      setLoading(false);
    }
  }

  async function fetchHistory() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  }

  async function handleApprove() {
    if (!confirm('Are you sure you want to approve this claim?')) return;
    
    setProcessing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/claims/${claimId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to approve');
      }
      alert('✅ Claim approved! Staff has been notified via WhatsApp.');
      fetchClaim();
      fetchHistory();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to approve claim');
    } finally {
      setProcessing(false);
    }
  }

  async function handleReject() {
    if (!rejectReason.trim()) {
      alert('Please enter a rejection reason');
      return;
    }
    
    setProcessing(true);
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
      alert('❌ Claim rejected! Staff has been notified via WhatsApp with the reason.');
      setShowRejectForm(false);
      setRejectReason('');
      fetchClaim();
      fetchHistory();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reject claim');
    } finally {
      setProcessing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-600">{error || 'Claim not found'}</p>
        <Link href="/claims" className="mt-4 inline-block text-indigo-600 hover:text-indigo-800">
          ← Back to Claims
        </Link>
      </div>
    );
  }

  const canProcess = claim.status_code === 'PENDING' || claim.status_code === 'APPEALED';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href="/claims" className="hover:text-indigo-600">Claims</Link>
        <span>/</span>
        <span className="text-gray-800 font-medium">{claim.claim_number}</span>
      </div>

      {/* Claim Header */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-3xl">{getCategoryIcon(claim.category_code)}</span>
              <div>
                <h1 className="text-2xl font-bold text-gray-800">{claim.claim_number}</h1>
                <p className="text-gray-500">{claim.category_name} Claim</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {(claim.appeal_count ?? 0) > 0 && (
              <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                🔄 Appeal #{claim.appeal_count}
              </span>
            )}
            <span className={`px-4 py-2 rounded-full text-sm font-semibold border ${getStatusColor(claim.status_code)}`}>
              {claim.status_name}
            </span>
          </div>
        </div>

        {/* Action Buttons for Pending/Appealed Claims */}
        {canProcess && (
          <div className="mt-6 pt-6 border-t">
            {claim.status_code === 'APPEALED' && (
              <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <p className="text-sm text-purple-800">
                  🔄 This claim has been appealed by the staff member. Please review and make a decision.
                </p>
              </div>
            )}
            {!showRejectForm ? (
              <div className="flex gap-4">
                <button
                  onClick={handleApprove}
                  disabled={processing}
                  className="flex-1 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {processing ? 'Processing...' : '✓ Approve Claim'}
                </button>
                <button
                  onClick={() => setShowRejectForm(true)}
                  disabled={processing}
                  className="flex-1 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  ✗ Reject Claim
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Rejection Reason <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Enter the reason for rejecting this claim..."
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    autoFocus
                  />
                </div>
                <div className="flex gap-4">
                  <button
                    onClick={handleReject}
                    disabled={processing || !rejectReason.trim()}
                    className="flex-1 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                  >
                    {processing ? 'Rejecting...' : 'Confirm Rejection'}
                  </button>
                  <button
                    onClick={() => { setShowRejectForm(false); setRejectReason(''); }}
                    className="flex-1 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Rejection Reason Display */}
        {claim.status_code === 'REJECTED' && claim.rejection_reason && (
          <div className="mt-6 pt-6 border-t">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm font-medium text-red-800">Rejection Reason:</p>
              <p className="text-red-700 mt-1">{claim.rejection_reason}</p>
            </div>
          </div>
        )}
      </div>

      {/* Status History Timeline */}
      {history.length > 0 && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>📜</span> Status History
          </h3>
          <div className="space-y-4">
            {history.map((item, index) => (
              <div key={item.id} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${getStatusColor(item.to_status_code)}`}>
                    {getStatusIcon(item.to_status_code)}
                  </div>
                  {index < history.length - 1 && (
                    <div className="w-0.5 h-full bg-gray-200 mt-2"></div>
                  )}
                </div>
                <div className="flex-1 pb-4">
                  <div className="flex items-center gap-2">
                    {item.from_status_name && (
                      <>
                        <span className="text-gray-500">{item.from_status_name}</span>
                        <span className="text-gray-400">→</span>
                      </>
                    )}
                    <span className="font-medium text-gray-800">{item.to_status_name}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{formatDate(item.created_at)}</p>
                  {item.changed_by_name && (
                    <p className="text-sm text-gray-500">By: {item.changed_by_name}</p>
                  )}
                  {item.reason && (
                    <p className="text-sm text-gray-600 mt-1 italic">"{item.reason}"</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Claim Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Employee Info */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>👤</span> Employee Details
          </h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-gray-500">Name</dt>
              <dd className="font-medium text-gray-800">{claim.employee_name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Code</dt>
              <dd className="font-medium text-gray-800">{claim.employee_code}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Grade</dt>
              <dd className="font-medium text-gray-800">{claim.grade_code || 'N/A'}</dd>
            </div>
            {claim.manager_name && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Manager</dt>
                <dd className="font-medium text-gray-800">{claim.manager_name}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Claim Info */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>📋</span> Claim Details
          </h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-gray-500">Category</dt>
              <dd className="font-medium text-gray-800">{claim.category_name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Type</dt>
              <dd className="font-medium text-gray-800 capitalize">{claim.claim_type}</dd>
            </div>
            {claim.location_name && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Location</dt>
                <dd className="font-medium text-gray-800">{claim.location_name}</dd>
              </div>
            )}
            {claim.duration_days > 1 && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Duration</dt>
                <dd className="font-medium text-gray-800">{claim.duration_days} days</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Amount Info */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>💰</span> Amount
          </h3>
          <dl className="space-y-3">
            {claim.user_amount && (
              <div className="flex justify-between">
                <dt className="text-gray-500">User Amount</dt>
                <dd className="font-medium text-gray-800">{formatCurrency(claim.user_amount)}</dd>
              </div>
            )}
            {claim.system_amount && (
              <div className="flex justify-between">
                <dt className="text-gray-500">System Amount</dt>
                <dd className="font-medium text-gray-800">{formatCurrency(claim.system_amount)}</dd>
              </div>
            )}
            <div className="flex justify-between pt-2 border-t">
              <dt className="text-gray-700 font-medium">Final Amount</dt>
              <dd className="font-bold text-xl text-indigo-600">
                {formatCurrency(claim.final_amount || claim.system_amount || claim.user_amount)}
              </dd>
            </div>
          </dl>
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>🕐</span> Timeline
          </h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-gray-500">Claim Date</dt>
              <dd className="font-medium text-gray-800">{formatDate(claim.claim_date)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Submitted</dt>
              <dd className="font-medium text-gray-800">{formatDate(claim.created_at)}</dd>
            </div>
            {claim.approved_at && (
              <div className="flex justify-between">
                <dt className="text-gray-500">
                  {claim.status_code === 'APPROVED' ? 'Approved' : 'Processed'}
                </dt>
                <dd className="font-medium text-gray-800">{formatDate(claim.approved_at)}</dd>
              </div>
            )}
            {claim.approver_name && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Processed By</dt>
                <dd className="font-medium text-gray-800">{claim.approver_name}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* Description */}
      {claim.description && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>📝</span> Description
          </h3>
          <p className="text-gray-700 whitespace-pre-wrap">{claim.description}</p>
        </div>
      )}

      {/* Back Button */}
      <div className="pt-4">
        <Link
          href="/claims"
          className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-800 font-medium"
        >
          ← Back to Claims
        </Link>
      </div>
    </div>
  );
}
