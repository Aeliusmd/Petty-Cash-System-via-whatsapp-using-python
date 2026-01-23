'use client';

import { useState, useEffect } from 'react';

interface Category {
  id: number;
  code: string;
  name: string;
  description: string | null;
  requires_receipt: boolean;
}

interface Location {
  id: number;
  code: string;
  name: string;
}

interface NewClaimModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function NewClaimModal({ isOpen, onClose, onSuccess }: NewClaimModalProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [categoryId, setCategoryId] = useState<string>('');
  const [locationId, setLocationId] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [receiptFiles, setReceiptFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);

  useEffect(() => {
    if (isOpen) {
      fetchDropdownData();
    }
  }, [isOpen]);

  async function fetchDropdownData() {
    try {
      const token = localStorage.getItem('auth_token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [categoriesRes, locationsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/categories`, { headers }),
        fetch(`${API_BASE_URL}/api/locations`, { headers })
      ]);

      if (categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategories(data.categories || []);
      }
      if (locationsRes.ok) {
        const data = await locationsRes.json();
        // API returns { locations: [...] } or direct array
        setLocations(Array.isArray(data) ? data : (data.locations || []));
      }
    } catch (err) {
      console.error('Failed to load dropdown data:', err);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length > 0) {
      setReceiptFiles(prev => [...prev, ...files]);
      const newUrls = files.map(file => file.type.startsWith('image/') ? URL.createObjectURL(file) : '');
      setPreviewUrls(prev => [...prev, ...newUrls]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!categoryId || !amount || receiptFiles.length === 0) {
      setError('Please fill in all required fields and upload at least one receipt');
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem('auth_token');
      const formData = new FormData();
      receiptFiles.forEach((file) => {
        formData.append('receipts', file);
      });
      formData.append('amount', amount);
      formData.append('category_id', categoryId);
      if (locationId) formData.append('location_id', locationId);
      if (description) formData.append('description', description);

      const res = await fetch(`${API_BASE_URL}/api/claims`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to submit claim');
      }

      const result = await res.json();
      console.log('Claim created:', result);
      
      // Reset form
      setCategoryId('');
      setLocationId('');
      setAmount('');
      setDescription('');
      setReceiptFiles([]);
      setPreviewUrls([]);
      
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit claim');
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 rounded-t-2xl">
          <h2 className="text-xl font-bold text-white">Submit New Claim</h2>
          <p className="text-indigo-100 text-sm">Upload your receipt and enter claim details</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Receipt Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
                Receipt Images <span className="text-red-500">*</span>
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-4 text-center hover:border-indigo-400 transition-colors">
              {receiptFiles.length > 0 ? (
                <div className="flex flex-wrap gap-4 justify-center">
                  {receiptFiles.map((file, idx) => (
                    <div key={idx} className="relative flex flex-col items-center">
                      {previewUrls[idx] && file.type.startsWith('image/') ? (
                        <img src={previewUrls[idx]} alt={`Receipt ${idx+1}`} className="max-h-32 rounded-lg mb-1" />
                      ) : (
                        <span className="text-2xl">📄</span>
                      )}
                      <span className="text-gray-600 text-xs max-w-[100px] truncate">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => {
                          setReceiptFiles(files => files.filter((_, i) => i !== idx));
                          setPreviewUrls(urls => urls.filter((_, i) => i !== idx));
                        }}
                        className="absolute top-0 right-0 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-red-600"
                        style={{transform: 'translate(40%, -40%)'}}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <label className="cursor-pointer">
                  <div className="text-4xl mb-2">📸</div>
                  <p className="text-gray-500">Click to upload receipts</p>
                  <p className="text-gray-400 text-xs mt-1">JPG, PNG or PDF up to 5MB each</p>
                  <input
                    type="file"
                    accept="image/*,.pdf"
                    multiple
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              )}
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category <span className="text-red-500">*</span>
            </label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              required
            >
              <option value="">Select a category</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name} ({cat.code})
                </option>
              ))}
            </select>
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Amount (Rs.) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="Enter claim amount"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              required
            />
          </div>

          {/* Location (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Location <span className="text-gray-400">(optional)</span>
            </label>
            <select
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">Select a location</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description <span className="text-gray-400">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add any additional details..."
              rows={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Submitting...
                </span>
              ) : (
                'Submit Claim'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
