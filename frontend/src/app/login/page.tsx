'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleRequestOTP(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/request-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: phoneNumber }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to send OTP');
      }

      const data = await res.json();
      console.log('OTP sent:', data.message);
      
      if (data.otp_code) {
        console.log('DEV OTP:', data.otp_code);
      }

      setStep('otp');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOTP(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: phoneNumber, otp_code: otpCode }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Invalid OTP code');
      }

      const data = await res.json();
      login(data.access_token, data.employee);

      // Redirect based on role
      if (data.employee.role === 'super_admin') {
        router.push('/organizations');  // Super admin goes to org list
      } else if (data.employee.role === 'admin' || data.employee.role === 'manager') {
        router.push('/claims');
      } else {
        router.push('/my-claims');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to verify OTP');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-white/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-white/10 rounded-full blur-3xl animate-pulse delay-700"></div>
      </div>

      {/* Login Card */}
      <div className="relative bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-8 w-full max-w-md border border-white/20">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="inline-block p-4 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl mb-4 shadow-lg">
            <span className="text-5xl">💰</span>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Petty Cash System
          </h1>
          <p className="text-gray-600 font-medium">Secure Employee Login</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg animate-shake">
            <p className="text-red-700 text-sm font-medium flex items-center gap-2">
              <span>⚠️</span>
              {error}
            </p>
          </div>
        )}

        {/* Phone Number Step */}
        {step === 'phone' && (
          <form onSubmit={handleRequestOTP} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                📱 Phone Number
              </label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="94771234567"
                required
                className="w-full px-5 py-4 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-200 focus:border-indigo-500 transition-all text-gray-800 font-medium placeholder-gray-400"
              />
              <p className="mt-3 text-sm text-gray-500 flex items-center gap-2">
                <span>ℹ️</span>
                Enter your registered phone number
              </p>
            </div>

            <button
              type="submit"
              disabled={loading || !phoneNumber}
              className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-4 rounded-xl font-bold text-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 active:scale-95 shadow-lg"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-3">
                  <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
                  Sending OTP...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <span>🔐</span>
                  Send OTP
                </span>
              )}
            </button>
          </form>
        )}

        {/* OTP Verification Step */}
        {step === 'otp' && (
          <form onSubmit={handleVerifyOTP} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                🔑 Enter OTP Code
              </label>
              <input
                type="text"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000"
                maxLength={6}
                required
                className="w-full px-5 py-5 border-2 border-gray-200 rounded-xl text-center text-3xl font-bold tracking-[0.5em] focus:ring-4 focus:ring-purple-200 focus:border-purple-500 transition-all text-gray-900 placeholder-gray-300"
              />
              <p className="mt-3 text-sm text-gray-600 flex items-center justify-center gap-2">
                <span>💬</span>
                Check your WhatsApp for the 6-digit code
              </p>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setStep('phone');
                  setOtpCode('');
                  setError('');
                }}
                className="flex-1 bg-gray-100 text-gray-700 py-4 rounded-xl font-bold hover:bg-gray-200 transition-all"
              >
                ← Back
              </button>
              <button
                type="submit"
                disabled={loading || otpCode.length !== 6}
                className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white py-4 rounded-xl font-bold hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 active:scale-95 shadow-lg"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
                    Verifying...
                  </span>
                ) : (
                  '✓ Verify & Login'
                )}
              </button>
            </div>
          </form>
        )}

        {/* Help Section */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <p className="text-center text-sm text-gray-500 flex items-center justify-center gap-2">
            <span>❓</span>
            Need help? Contact your administrator
          </p>
        </div>
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
