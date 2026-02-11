'use client';

import Link from 'next/link';
import { useDashboard } from '@/hooks/useDashboard';
import RecentActivityList from '@/components/RecentActivityList';

export default function DashboardPage() {
  const { stats, loading, user, canViewDashboard, isAuthenticated } = useDashboard();

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated || !canViewDashboard) {
    return null;
  }

  if (!stats) return null;

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Welcome back, {user?.name}! 👋</h1>
          {user?.organization_name && (
            <div className="text-2xl font-semibold text-white mb-2 flex items-center gap-2">
              <span className="opacity-80">Organization:</span>
              <span>{user.organization_name}</span>
            </div>
          )}
          <p className="text-indigo-100 text-lg">Here's what's happening in your Petty Cash system. • Auto-refreshes every 10s</p>
        </div>
        <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform translate-x-12"></div>
      </div>

      {/* Stats Grid - RAM Pattern */}
      <div className="grid gap-6" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
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

      <div className="grid gap-8" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 500px), 1fr))" }}>
        {/* Recent Activity */}
        <div className="lg:col-span-2">
          <RecentActivityList claims={stats.recent_claims} />
        </div>

        {/* Categories Chart */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-bold text-gray-800 mb-6">Spending by Category</h3>
          <div className="space-y-6">
            {stats.categories.slice(0, 5).map((cat) => (
              <div key={cat.category}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700">{cat.category}</span>
                  <span className="text-gray-500">LKR {(cat.total_amount || 0).toLocaleString()}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-indigo-600 h-2 rounded-full"
                    style={{
                      width: `${((cat.total_amount || 0) / Math.max(...stats.categories.map(c => c.total_amount || 0), 1)) * 100}%`
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
