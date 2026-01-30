'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

interface Organization {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export default function OrganizationsPage() {
  const router = useRouter();
  const { isSuperAdmin, token, enterOrganization, isLoading } = useAuth();
  const [units, setUnits] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingUnit, setEditingUnit] = useState<Organization | null>(null);
  const [formData, setFormData] = useState({ code: '', name: '' });
  const [enteringUnitId, setEnteringUnitId] = useState<number | null>(null);

  useEffect(() => {
    if (isLoading) return;

    // Check super admin access
    if (!isSuperAdmin) {
      setAccessDenied(true);
      setLoading(false);
      // Redirect after showing message
      setTimeout(() => router.push('/'), 2000);
      return;
    }
    fetchUnits();
  }, [isSuperAdmin, router, isLoading]);

  const fetchUnits = async () => {
    try {
      const authToken = localStorage.getItem('auth_token');
      console.log('🔑 Fetching organizations with token:', authToken ? authToken.substring(0, 10) + '...' : 'null');
      
      const res = await fetch('http://localhost:4101/api/organizations', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      
      console.log(`📡 API Status: ${res.status} ${res.statusText}`);
      
      const text = await res.text();
      console.log('📦 Raw API Response:', text);
      
      if (!res.ok) {
        console.error('❌ API Error:', res.status, text);
        if (res.status === 401) {
            console.error('Unauthorized - Token might be invalid');
        }
        setUnits([]);
        return;
      }

      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        console.error('❌ Failed to parse JSON:', e);
        setUnits([]);
        return;
      }
      
      // Ensure we always set an array
      if (Array.isArray(data)) {
        setUnits(data);
      } else if (data.organizations && Array.isArray(data.organizations)) {
        setUnits(data.organizations);
      } else {
        console.error('Unexpected API response format:', data);
        setUnits([]);
      }
    } catch (error) {
      console.error('Error fetching units:', error);
      setUnits([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const authToken = localStorage.getItem('auth_token');
      const url = editingUnit 
        ? `http://localhost:4101/api/organizations/${editingUnit.id}`
        : 'http://localhost:4101/api/organizations';
      
      const res = await fetch(url, {
        method: editingUnit ? 'PUT' : 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        fetchUnits();
        setShowAddModal(false);
        setEditingUnit(null);
        setFormData({ code: '', name: '' });
      }
    } catch (error) {
      console.error('Error saving unit:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this organization?')) return;
    
    try {
      const authToken = localStorage.getItem('auth_token');
      const res = await fetch(`http://localhost:4101/api/organizations/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      if (res.ok) {
        fetchUnits();
      }
    } catch (error) {
      console.error('Error deleting unit:', error);
    }
  };

  const handleEnter = async (orgId: number) => {
    try {
      setEnteringUnitId(orgId);
      await enterOrganization(orgId);
    } catch (error) {
      console.error('Failed to enter organization:', error);
      alert('Failed to enter organization. Please checking logs.');
    } finally {
      setEnteringUnitId(null);
    }
  };

  return (
    <div className="container mx-auto p-6">
      {accessDenied ? (
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="text-red-500 text-6xl mb-4">🚫</div>
          <h1 className="text-2xl font-bold text-red-600 mb-2">Access Denied</h1>
          <p className="text-gray-600">Super Admin privileges required to access this page.</p>
          <p className="text-gray-400 text-sm mt-2">Redirecting to dashboard...</p>
        </div>
      ) : loading ? (
        <p>Loading...</p>
      ) : (
        <>
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold">Organizations / Units</h1>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              + Add Organization
            </button>
          </div>
          <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {units.map((unit) => (
                <tr key={unit.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-mono text-gray-700">{unit.code}</td>
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{unit.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs ${unit.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {unit.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap space-x-2">
                      <button
                        onClick={() => handleEnter(unit.id)}
                        disabled={enteringUnitId === unit.id}
                        className={`px-3 py-1 text-white rounded text-sm font-medium ${
                          enteringUnitId === unit.id 
                            ? 'bg-indigo-400 cursor-not-allowed' 
                            : 'bg-indigo-600 hover:bg-indigo-700'
                        }`}
                      >
                        {enteringUnitId === unit.id ? 'Entering...' : 'Enter →'}
                      </button>
                    <button
                      onClick={() => {
                        setEditingUnit(unit);
                        setFormData({ code: unit.code, name: unit.name });
                        setShowAddModal(true);
                      }}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(unit.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
      )}

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <h2 className="text-xl font-bold mb-4">
              {editingUnit ? 'Edit Organization' : 'Add Organization'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Code</label>
                <input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData({...formData, code: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingUnit(null);
                    setFormData({ code: '', name: '' });
                  }}
                  className="px-4 py-2 border rounded hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  {editingUnit ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
