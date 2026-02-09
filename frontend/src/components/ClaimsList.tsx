import Link from 'next/link';
import { useState } from 'react';

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
  final_amount: number | null;
  user_amount: number | null;
  system_amount: number | null;
  claim_date: string;
  created_at: string;
  claim_type: string;
  duration_days: number;
  description: string | null;
  rejection_reason: string | null;
  appeal_count: number | null;
  manager_name?: string | null;
  approver_name?: string | null;
  approved_at?: string | null;
}

interface ClaimsListProps {
  claims: Claim[];
  loading: boolean;
  processingId: number | null;
  onView: (claim: Claim) => void;
  onApprove: (id: number) => void;
  onReject: (id: number, reason: string) => void;
  onDelete: (id: number, claimNumber: string) => void;
}

// Helper functions (duplicated for self-containment)
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

function getClaimStatusDisplay(claim: Claim) {
    if (claim.status_code === 'APPROVED' && claim.appeal_count && claim.appeal_count > 0) {
      return 'Appeal & Approved';
    }
    return claim.status_name;
}

export default function ClaimsList({ 
  claims, 
  loading, 
  processingId, 
  onView, 
  onApprove, 
  onReject, 
  onDelete 
}: ClaimsListProps) {
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const handleRejectClick = (id: number) => {
    setRejectingId(id);
    setRejectReason('');
  };

  const cancelReject = () => {
    setRejectingId(null);
    setRejectReason('');
  };

  const confirmReject = (id: number) => {
    if (rejectReason.trim()) {
      onReject(id, rejectReason);
      setRejectingId(null);
      setRejectReason('');
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 flex justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (claims.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 text-center text-gray-900">
        No claims found
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto">
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
                    onClick={() => onView(claim)}
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
                        onClick={() => onApprove(claim.id)}
                        disabled={processingId === claim.id}
                        className="px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                      >
                        {processingId === claim.id ? '...' : '✓ Approve'}
                      </button>
                      <button
                        onClick={() => handleRejectClick(claim.id)}
                        disabled={processingId === claim.id}
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
                        onClick={() => confirmReject(claim.id)}
                        disabled={processingId === claim.id || !rejectReason.trim()}
                        className="px-2 py-1 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700 disabled:opacity-50"
                      >
                         {processingId === claim.id ? '...' : 'Confirm'}
                      </button>
                      <button
                        onClick={cancelReject}
                        className="px-2 py-1 bg-gray-200 text-gray-900 text-xs font-medium rounded hover:bg-gray-300"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                  {claim.status_code === 'REJECTED' && claim.rejection_reason && (
                    <p className="text-sm text-red-600">Reason: {claim.rejection_reason}</p>
                  )}
                  <button
                    onClick={() => onDelete(claim.id, claim.claim_number)}
                    disabled={processingId === claim.id}
                    className="mt-2 px-2 py-1 text-xs text-red-500 hover:text-red-700 hover:underline"
                  >
                    🗑️ Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden divide-y divide-gray-100">
        {claims.map((claim) => (
          <div key={claim.id} className="p-4 bg-white hover:bg-gray-50 transition-colors">
            {/* Header: Claim # and Status */}
            <div className="flex justify-between items-start mb-3">
              <div>
                 <Link href={`/claims/${claim.id}`} className="text-sm font-bold text-indigo-600 hover:text-indigo-800">
                    {claim.claim_number}
                  </Link>
                  <div className="text-xs text-gray-500 mt-1">{formatDate(claim.claim_date)}</div>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(claim.status_code)}`}>
                 {getClaimStatusDisplay(claim)}
              </span>
            </div>

            {/* Content: Employee & Category */}
            <div className="grid grid-cols-2 gap-2 mb-3">
               <div>
                  <div className="text-xs text-gray-500 mb-0.5">Employee</div>
                  <div className="text-sm font-medium text-gray-800">{claim.employee_name}</div>
               </div>
               <div className="text-right">
                  <div className="text-xs text-gray-500 mb-0.5">Amount</div>
                  <div className="text-sm font-bold text-gray-900">
                    {formatCurrency(claim.final_amount || claim.system_amount || claim.user_amount)}
                  </div>
               </div>
            </div>
            
             <div className="flex items-center gap-2 mb-3 text-sm text-gray-700 bg-gray-50 p-2 rounded">
                <span>{getCategoryIcon(claim.category_code)}</span>
                <span>{claim.category_name}</span>
                {claim.location_name && (
                   <>
                    <span className="text-gray-300">|</span>
                    <span>📍 {claim.location_name}</span>
                   </>
                )}
             </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-gray-100">
              <button
                 onClick={() => onView(claim)}
                 className="flex-1 py-2.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded hover:bg-indigo-100 active:bg-indigo-200 transition-colors"
              >
                View Details
              </button>

              {(claim.status_code === 'PENDING' || claim.status_code === 'APPEALED') && rejectingId !== claim.id && (
                <>
                  <button
                    onClick={() => onApprove(claim.id)}
                    disabled={processingId === claim.id}
                    className="flex-1 py-2.5 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 border border-green-200 active:bg-green-200 transition-colors"
                  >
                    Approve
                  </button>
                   <button
                    onClick={() => handleRejectClick(claim.id)}
                    disabled={processingId === claim.id}
                    className="flex-1 py-2.5 text-xs font-medium text-red-700 bg-red-50 rounded hover:bg-red-100 border border-red-200 active:bg-red-200 transition-colors"
                  >
                    Reject
                  </button>
                </>
              )}

               {(claim.status_code === 'PENDING' || claim.status_code === 'APPEALED') && rejectingId === claim.id && (
                 <div className="w-full mt-2">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Rejection reason..."
                        className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-red-500"
                        autoFocus
                      />
                    </div>
                     <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => confirmReject(claim.id)}
                          disabled={processingId === claim.id || !rejectReason.trim()}
                          className="flex-1 py-1.5 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700"
                        >
                          Confirm Reject
                        </button>
                        <button
                          onClick={cancelReject}
                          className="px-3 py-1.5 bg-gray-200 text-gray-800 text-xs font-medium rounded hover:bg-gray-300"
                        >
                          Cancel
                        </button>
                     </div>
                 </div>
               )}

               <button
                  onClick={() => onDelete(claim.id, claim.claim_number)}
                  disabled={processingId === claim.id}
                  className="px-3 py-1.5 text-xs font-medium text-red-500 hover:text-red-700"
               >
                 Delete
               </button>
            </div>
            {claim.status_code === 'REJECTED' && claim.rejection_reason && (
                <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                   Reason: {claim.rejection_reason}
                </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
