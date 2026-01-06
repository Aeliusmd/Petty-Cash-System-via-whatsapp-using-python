'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import Link from 'next/link';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

interface DashboardStats {
  overview: {
    total_claims: number;
    pending_claims: number;
    approved_claims: number;
    rejected_claims: number;
    total_approved_amount: number;
    pending_amount: number;
  };
  categories: {
    category: number;
    count: number;
    total_amount: number;
  }[];
  recent_claims: {
    claim_number: string;
    created_at: string;
    employee_name: string;
    category_name: string;
    final_amount: number;
    status_code: string;
  }[];
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isAdmin, isManager } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    // Role-based redirect for pure employees
    if (!isAdmin && !isManager) {
      router.push('/my-claims');
      return;
    }

    fetchStats();
  }, [isAuthenticated, isAdmin, isManager, router]);

  async function fetchStats() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Welcome back, {user?.name}! 👋</h1>
          <p className="text-indigo-100 text-lg">Here's what's happening in your Petty Cash system.</p>
        </div>
        <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform translate-x-12"></div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
          <div className="text-gray-500 text-sm font-medium mb-1">Total Claims</div>
          <div className="text-3xl font-bold text-gray-800">{stats.overview.total_claims}</div>
          <div className="mt-2 text-sm text-gray-400">Lifetime volume</div>
        </div>
        
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-orange-100 hover:shadow-md transition-shadow">
          <div className="text-orange-600 text-sm font-medium mb-1">Pending Approval</div>
          <div className="text-3xl font-bold text-gray-800">{stats.overview.pending_claims}</div>
          <div className="mt-2 text-sm text-orange-600 font-medium">
            LKR {stats.overview.pending_amount.toLocaleString()}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-green-100 hover:shadow-md transition-shadow">
          <div className="text-green-600 text-sm font-medium mb-1">Approved Claims</div>
          <div className="text-3xl font-bold text-gray-800">{stats.overview.approved_claims}</div>
          <div className="mt-2 text-sm text-green-600 font-medium">
            LKR {stats.overview.total_approved_amount.toLocaleString()}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-red-100 hover:shadow-md transition-shadow">
          <div className="text-red-500 text-sm font-medium mb-1">Rejected Claims</div>
          <div className="text-3xl font-bold text-gray-800">{stats.overview.rejected_claims}</div>
          <div className="mt-2 text-sm text-red-500">
            {((stats.overview.rejected_claims / (stats.overview.total_claims || 1)) * 100).toFixed(1)}% rate
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Activity */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex justify-between items-center">
            <h3 className="font-bold text-gray-800">Recent Claims</h3>
            <Link href="/claims" className="text-indigo-600 text-sm font-medium hover:text-indigo-800">
              View All →
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-500 uppercase bg-gray-50">
                <tr>
                  <th className="px-6 py-3">Claim</th>
                  <th className="px-6 py-3">Employee</th>
                  <th className="px-6 py-3">Amount</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Date</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_claims.map((claim) => (
                  <tr key={claim.claim_number} className="bg-white border-b hover:bg-gray-50">
                    <td className="px-6 py-4 font-medium text-gray-900">
                      {claim.claim_number}
                      <span className="block text-xs text-gray-400 font-normal">{claim.category_name}</span>
                    </td>
                    <td className="px-6 py-4">{claim.employee_name}</td>
                    <td className="px-6 py-4">LKR {claim.final_amount.toLocaleString()}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        claim.status_code === 'APPROVED' ? 'bg-green-100 text-green-800' :
                        claim.status_code === 'REJECTED' ? 'bg-red-100 text-red-800' :
                        'bg-orange-100 text-orange-800'
                      }`}>
                        {claim.status_code}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-500">
                      {new Date(claim.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Categories Chart */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-bold text-gray-800 mb-6">Spending by Category</h3>
          <div className="space-y-6">
            {stats.categories.slice(0, 5).map((cat) => (
              <div key={cat.category}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700">{cat.category}</span>
                  <span className="text-gray-500">LKR {cat.total_amount.toLocaleString()}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-indigo-600 h-2 rounded-full"
                    style={{
                      width: `${(cat.total_amount / Math.max(...stats.categories.map(c => c.total_amount))) * 100}%`
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
