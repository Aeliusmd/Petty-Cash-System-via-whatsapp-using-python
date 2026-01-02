'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Stats {
  overview: {
    total_claims: number;
    pending_claims: number;
    approved_claims: number;
    rejected_claims: number;
    total_approved_amount: number;
    pending_amount: number;
  };
  categories: Array<{
    category: string;
    category_code: string;
    count: number;
    total_amount: number;
  }>;
  recent_claims: Array<{
    claim_number: string;
    created_at: string;
    employee_name: string;
    category_name: string;
    final_amount: number;
    status_code: string;
  }>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

function formatCurrency(amount: number | null): string {
  if (amount === null || amount === undefined) return 'Rs.0';
  return `Rs.${amount.toLocaleString()}`;
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'PENDING': return 'bg-yellow-100 text-yellow-800';
    case 'APPROVED': return 'bg-green-100 text-green-800';
    case 'REJECTED': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/stats`);
        if (!res.ok) throw new Error('Failed to fetch stats');
        const data = await res.json();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-600">{error}</p>
        <p className="text-sm text-gray-900 mt-2">Make sure the backend is running on port 4101</p>
      </div>
    );
  }

  const overview = stats?.overview || {
    total_claims: 0,
    pending_claims: 0,
    approved_claims: 0,
    rejected_claims: 0,
    total_approved_amount: 0,
    pending_amount: 0,
  };

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Dashboard</h2>
        <p className="text-gray-900">Overview of petty cash claims</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-indigo-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-900 uppercase tracking-wide">Total Claims</p>
              <p className="text-3xl font-bold text-gray-800">{overview.total_claims}</p>
            </div>
            <span className="text-3xl">📋</span>
          </div>
        </div>

        <Link href="/claims?status=PENDING" className="block">
          <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-yellow-500 hover:shadow-lg transition-shadow cursor-pointer">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-900 uppercase tracking-wide">Pending</p>
                <p className="text-3xl font-bold text-yellow-600">{overview.pending_claims}</p>
                <p className="text-sm text-gray-900 mt-1">{formatCurrency(overview.pending_amount)}</p>
              </div>
              <span className="text-3xl">⏳</span>
            </div>
          </div>
        </Link>

        <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-900 uppercase tracking-wide">Approved</p>
              <p className="text-3xl font-bold text-green-600">{overview.approved_claims}</p>
              <p className="text-sm text-gray-900 mt-1">{formatCurrency(overview.total_approved_amount)}</p>
            </div>
            <span className="text-3xl">✅</span>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-900 uppercase tracking-wide">Rejected</p>
              <p className="text-3xl font-bold text-red-600">{overview.rejected_claims}</p>
            </div>
            <span className="text-3xl">❌</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Claims */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <div className="bg-gray-50 px-6 py-4 border-b flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Recent Claims</h3>
            <Link href="/claims" className="text-sm text-indigo-600 hover:text-indigo-800">
              View All →
            </Link>
          </div>
          <div className="divide-y">
            {stats?.recent_claims?.length ? (
              stats.recent_claims.map((claim, index) => (
                <div key={index} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-800">{claim.claim_number}</p>
                      <p className="text-sm text-gray-900">{claim.employee_name} • {claim.category_name}</p>
                    </div>
                    <div className="text-right">
                      <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(claim.status_code)}`}>
                        {claim.status_code}
                      </span>
                      <p className="text-sm font-medium text-gray-900 mt-1">{formatCurrency(claim.final_amount)}</p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-6 py-8 text-center text-gray-900">
                No claims yet
              </div>
            )}
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <div className="bg-gray-50 px-6 py-4 border-b">
            <h3 className="font-semibold text-gray-800">Approved by Category</h3>
          </div>
          <div className="divide-y">
            {stats?.categories?.length ? (
              stats.categories.map((cat, index) => (
                <div key={index} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">
                      {cat.category_code === 'BATTA' ? '🏷️' : 
                       cat.category_code === 'FUEL' ? '⛽' :
                       cat.category_code === 'ACCOM' ? '🏨' : '📦'}
                    </span>
                    <div>
                      <p className="font-medium text-gray-800">{cat.category}</p>
                      <p className="text-sm text-gray-900">{cat.count} claims</p>
                    </div>
                  </div>
                  <p className="font-semibold text-gray-800">{formatCurrency(cat.total_amount)}</p>
                </div>
              ))
            ) : (
              <div className="px-6 py-8 text-center text-gray-900">
                No approved claims yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
