'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function SignupPage() {
  const router = useRouter();
  
  const [formData, setFormData] = useState({
    org_name: '',
    admin_name: '',
    admin_phone: '',
    admin_email: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [createdData, setCreatedData] = useState<any>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create organization');
      }

      setSuccess(true);
      setCreatedData(data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create organization');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-600 via-teal-600 to-cyan-500 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-white/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-white/10 rounded-full blur-3xl animate-pulse delay-700"></div>
      </div>

      {/* Card */}
      <div className="relative bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-8 w-full max-w-md border border-white/20">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="inline-block p-4 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl mb-4 shadow-lg">
            <span className="text-5xl">🏢</span>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent mb-2">
            Create Organization
          </h1>
          <p className="text-gray-600 font-medium">Set up your petty cash system</p>
        </div>

        {/* Success State */}
        {success && createdData ? (
          <div className="space-y-6">
            <div className="p-4 bg-emerald-50 border-l-4 border-emerald-500 rounded-lg">
              <p className="text-emerald-700 font-bold flex items-center gap-2 mb-2">
                <span>✅</span>
                Organization Created Successfully!
              </p>
              <p className="text-emerald-600 text-sm">
                Your organization <strong>{createdData.organization?.name}</strong> is ready.
              </p>
            </div>

            <div className="bg-gray-50 rounded-xl p-4 space-y-3">
              <h3 className="font-bold text-gray-800">📋 Your Details</h3>
              
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Organization:</span>
                  <span className="font-medium text-gray-800">{createdData.organization?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Org Code:</span>
                  <span className="font-mono text-gray-800">{createdData.organization?.code}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Admin Name:</span>
                  <span className="font-medium text-gray-800">{createdData.admin?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Login Phone:</span>
                  <span className="font-mono text-gray-800">{createdData.admin?.phone_number}</span>
                </div>
              </div>
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
              <p className="text-blue-700 text-sm font-medium">
                💡 You can now login with your phone number to access your organization.
              </p>
            </div>

            <Link
              href="/login"
              className="block w-full bg-gradient-to-r from-emerald-600 to-teal-600 text-white py-4 rounded-xl font-bold text-lg text-center hover:from-emerald-700 hover:to-teal-700 transition-all transform hover:scale-105 active:scale-95 shadow-lg"
            >
              Go to Login →
            </Link>
          </div>
        ) : (
          <>
            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg animate-shake">
                <p className="text-red-700 text-sm font-medium flex items-center gap-2">
                  <span>⚠️</span>
                  {error}
                </p>
              </div>
            )}

            {/* Signup Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Organization Name */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  🏢 Organization Name
                </label>
                <input
                  type="text"
                  name="org_name"
                  value={formData.org_name}
                  onChange={handleChange}
                  placeholder="Your Company Ltd"
                  required
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-emerald-200 focus:border-emerald-500 transition-all text-gray-800 font-medium placeholder-gray-400"
                />
              </div>

              {/* Admin Name */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  👤 Admin Full Name
                </label>
                <input
                  type="text"
                  name="admin_name"
                  value={formData.admin_name}
                  onChange={handleChange}
                  placeholder="John Doe"
                  required
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-emerald-200 focus:border-emerald-500 transition-all text-gray-800 font-medium placeholder-gray-400"
                />
              </div>

              {/* Admin Phone */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  📱 Admin Phone Number
                </label>
                <input
                  type="tel"
                  name="admin_phone"
                  value={formData.admin_phone}
                  onChange={handleChange}
                  placeholder="94771234567"
                  required
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-emerald-200 focus:border-emerald-500 transition-all text-gray-800 font-medium placeholder-gray-400"
                />
                <p className="mt-2 text-xs text-gray-500">
                  This phone number will be used for login
                </p>
              </div>

              {/* Admin Email (Optional) */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  ✉️ Admin Email <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  type="email"
                  name="admin_email"
                  value={formData.admin_email}
                  onChange={handleChange}
                  placeholder="admin@company.com"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-emerald-200 focus:border-emerald-500 transition-all text-gray-800 font-medium placeholder-gray-400"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading || !formData.org_name || !formData.admin_name || !formData.admin_phone}
                className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 text-white py-4 rounded-xl font-bold text-lg hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 active:scale-95 shadow-lg"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-3">
                    <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
                    Creating Organization...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <span>🚀</span>
                    Create Organization
                  </span>
                )}
              </button>
            </form>

            {/* Back to Login */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <p className="text-center text-sm text-gray-600">
                Already have an account?{' '}
                <Link href="/login" className="text-emerald-600 font-bold hover:underline">
                  Login
                </Link>
              </p>
            </div>
          </>
        )}
      </div>

      <style jsx>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-10px); }
          75% { transform: translateX(10px); }
        }
        .animate-shake {
          animation: shake 0.3s ease-in-out;
        }
      `}</style>
    </div>
  );
}
