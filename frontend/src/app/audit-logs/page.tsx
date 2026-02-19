'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { authenticatedFetch } from '@/utils/api';

interface AuditLog {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  old_values: any;
  new_values: any;
  performed_by: number;
  performed_by_name: string;
  performed_by_code: string;
  ip_address: string;
  user_agent: string;
  organization_name: string;
  metadata: any;
  created_at: string;
  description?: string; // Human-readable description
}

interface FilterState {
  entity_type: string;
  action: string;
  from_date: string;
  to_date: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function AuditLogsPage() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading, hasPermission } = useAuth();
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [accessRevoked, setAccessRevoked] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    entity_type: '',
    action: '',
    from_date: '',
    to_date: '',
  });

  // Permission-based access
  const canViewAuditLogs = hasPermission('audit.view');

  useEffect(() => {
    if (isLoading) return; // Wait for user data to be loaded
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    if (!canViewAuditLogs) {
      alert('Access denied. Audit view permission required.');
      router.push('/');
      return;
    }
  }, [isAuthenticated, isLoading, canViewAuditLogs, router]);

  useEffect(() => {
    if (isAuthenticated && canViewAuditLogs && !isLoading && !accessRevoked) {
      fetchAuditLogs();
      
      // Auto-refresh every 10 seconds
      const interval = setInterval(() => {
        fetchAuditLogs(true);
      }, 10000);
      
      return () => clearInterval(interval);
    }
  }, [page, filters, isAuthenticated, isLoading, canViewAuditLogs, accessRevoked]);



  const fetchAuditLogs = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      if (!token) {
        return;
      }

      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: (page * limit).toString(),
      });

      if (filters.entity_type) params.append('entity_type', filters.entity_type);
      if (filters.action) params.append('action', filters.action);
      if (filters.from_date) params.append('from_date', filters.from_date);
      if (filters.to_date) params.append('to_date', filters.to_date);

      const response = await authenticatedFetch(`${API_BASE_URL}/api/audit-logs?${params}`);

      if (response.status === 401) {
        return;
      }

      if (response.status === 403) {
        // Permission was revoked – stop all future requests immediately
        setAccessRevoked(true);
        if (!silent) {
          alert('Access denied. You no longer have permission to view audit logs.');
        }
        router.push('/');
        return;
      }

      const data = await response.json(); 
      
      if (!response.ok) throw new Error('Failed to fetch audit logs');

      setAuditLogs(data.audit_logs || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Error fetching audit logs:', error);
      // Don't show alert on auto-refresh errors
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      if (!token) return;

      const params = new URLSearchParams();
      if (filters.entity_type) params.append('entity_type', filters.entity_type);
      if (filters.action) params.append('action', filters.action);
      if (filters.from_date) params.append('from_date', filters.from_date);
      if (filters.to_date) params.append('to_date', filters.to_date);

      const response = await authenticatedFetch(`${API_BASE_URL}/api/audit-logs/export?${params}`);

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting audit logs:', error);
      alert('Failed to export audit logs');
    }
  };

  const getActionColor = (action: string) => {
    const colors: Record<string, string> = {
      CREATE: 'text-green-600 bg-green-50',
      UPDATE: 'text-blue-600 bg-blue-50',
      DELETE: 'text-red-600 bg-red-50',
      APPROVE: 'text-green-600 bg-green-50',
      REJECT: 'text-red-600 bg-red-50',
      LOGIN: 'text-purple-600 bg-purple-50',
      LOGOUT: 'text-gray-600 bg-gray-50',
      ENTER_ORG: 'text-indigo-600 bg-indigo-50',
      EXIT_ORG: 'text-indigo-600 bg-indigo-50',
      ENTER: 'text-indigo-600 bg-indigo-50',
      EXIT: 'text-indigo-600 bg-indigo-50',
    };
    return colors[action] || 'text-gray-600 bg-gray-50';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Parse markdown-style bold text for rendering
  const renderDescription = (description: string) => {
    if (!description) return description;
    
    // Split by ** markers and render bold text
    const parts = description.split('**');
    return parts.map((part, index) => {
      if (index % 2 === 1) {
        // Odd indices are bold text
        return <strong key={index} className="font-semibold text-gray-900">{part}</strong>;
      }
      return <span key={index}>{part}</span>;
    });
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Audit Logs</h2>
          <p className="text-gray-900">Track all system activities and changes</p>
        </div>
        <div className="text-sm text-gray-500">
          {auditLogs.length > 0 && (
            <span className="inline-flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Live
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4">Filters</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Entity Type
              </label>
              <select
                value={filters.entity_type}
                onChange={(e) => setFilters({ ...filters, entity_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Types</option>
                <option value="claim">Claim</option>
                <option value="employee">Employee</option>
                <option value="auth">Authentication</option>
                <option value="organization">Organization</option>
                <option value="receipt">Receipt</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Action
              </label>
              <select
                value={filters.action}
                onChange={(e) => setFilters({ ...filters, action: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Actions</option>
                <option value="CREATE">Create</option>
                <option value="UPDATE">Update</option>
                <option value="DELETE">Delete</option>
                <option value="APPROVE">Approve</option>
                <option value="REJECT">Reject</option>
                <option value="LOGIN">Login</option>
                <option value="LOGOUT">Logout</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                From Date
              </label>
              <input
                type="date"
                value={filters.from_date}
                onChange={(e) => setFilters({ ...filters, from_date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                To Date
              </label>
              <input
                type="date"
                value={filters.to_date}
                onChange={(e) => setFilters({ ...filters, to_date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={() => {
                setFilters({ entity_type: '', action: '', from_date: '', to_date: '' });
                setPage(0);
              }}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              Reset Filters
            </button>
            <button
              onClick={handleExport}
              className="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              📥 Export CSV
            </button>
          </div>
        </div>

        {/* Audit Logs Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading audit logs...</p>
            </div>
          ) : auditLogs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No audit logs found
            </div>
          ) : (
            <>
              <div className="divide-y divide-gray-200">
                {auditLogs.map((log) => (
                  <div key={log.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      {/* Main content - Description */}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-gray-900 mb-2">
                          {log.description ? renderDescription(log.description) : 'No description available'}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            🕐 {formatDate(log.created_at)}
                          </span>
                          <span className="flex items-center gap-1">
                            📍 {log.ip_address || 'N/A'}
                          </span>
                          <span className="flex items-center gap-1">
                            #{log.entity_type}
                          </span>
                        </div>
                      </div>
                      
                      {/* Action badge */}
                      <div>
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getActionColor(log.action)}`}>
                          {log.action}
                        </span>
                      </div>
                      
                      {/* Expand button for details */}
                      <div>
                        <button
                          onClick={() => setExpandedRow(expandedRow === log.id ? null : log.id)}
                          className="text-blue-600 hover:text-blue-800 text-sm"
                        >
                          {expandedRow === log.id ? '▼ Hide' : '▶ Details'}
                        </button>
                      </div>
                    </div>
                    
                    {/* Expanded details */}
                    {expandedRow === log.id && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="font-semibold text-gray-700">Performed by:</span>
                            <span className="ml-2 text-gray-900">{log.performed_by_name || 'System'}</span>
                            {log.performed_by_code && (
                              <span className="ml-1 text-gray-500">({log.performed_by_code})</span>
                            )}
                          </div>
                          <div>
                            <span className="font-semibold text-gray-700">Organization:</span>
                            <span className="ml-2 text-gray-900">{log.organization_name || 'N/A'}</span>
                          </div>
                          {log.user_agent && (
                            <div className="col-span-2">
                              <span className="font-semibold text-gray-700">User Agent:</span>
                              <span className="ml-2 text-gray-600 text-xs">{log.user_agent}</span>
                            </div>
                          )}
                          {log.metadata && Object.keys(log.metadata).length > 0 && (
                            <div className="col-span-2">
                              <span className="font-semibold text-gray-700 block mb-1">Metadata:</span>
                              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-32">
                                {JSON.stringify(log.metadata, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Pagination */}
              <div className="bg-white px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                <div className="text-sm text-gray-700">
                  Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} results
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-sm text-gray-700">
                    Page {page + 1} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
  );
}
