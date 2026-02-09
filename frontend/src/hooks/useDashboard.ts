import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { fetchStats, Stats } from '@/utils/api';

export function useDashboard() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, hasAnyPermission } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  // Permission-based access check
  const canViewDashboard = hasAnyPermission(['dashboard.view.org', 'dashboard.view.team']);

  useEffect(() => {
    // If auth is loading, do nothing yet
    if (isLoading) return;

    // Not authenticated -> Redirect to login
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    // No dashboard permission -> Redirect to appropriate page
    if (!canViewDashboard) {
      // Find a page they CAN access
      const permissions = user?.permissions || [];
      if (permissions.some((p: string) => ['claims.read.all', 'claims.read.team', 'claims.approve'].includes(p))) {
        router.push('/claims');
      } else if (permissions.some((p: string) => ['claims.read.own', 'claims.create'].includes(p))) {
        router.push('/my-claims');
      } else if (permissions.includes('audit.view')) {
        router.push('/audit-logs');
      } else if (permissions.some((p: string) => ['config.view', 'config.manage'].includes(p))) {
        router.push('/settings');
      } else if (permissions.includes('employees.read.all')) {
        router.push('/employees');
      }
      // If none match, stay on dashboard (will show loading or empty state)
      return;
    }

    // If we're here, we are authenticated and authorized to view dashboard
    loadStats();
  }, [isAuthenticated, canViewDashboard, isLoading, router, user]);

  async function loadStats() {
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoadingStats(false);
    }
  }

  return {
    stats,
    loading: isLoading || loadingStats,
    user,
    canViewDashboard,
    isAuthenticated
  };
}
