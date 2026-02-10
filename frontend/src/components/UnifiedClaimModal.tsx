'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';

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

interface UnifiedClaimModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type ClaimType = 'reimbursement' | 'advance';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function UnifiedClaimModal({ isOpen, onClose, onSuccess }: UnifiedClaimModalProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Claim type toggle
  const [claimType, setClaimType] = useState<ClaimType>('reimbursement');
  
  // Form state
  const [categoryId, setCategoryId] = useState<string>('');
  const [locationId, setLocationId] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [files, setFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  
  // Auto-calculated amount from files (for both types)
  const [extractedAmounts, setExtractedAmounts] = useState<number[]>([]);

  useEffect(() => {
    if (isOpen) {
      fetchDropdownData();
      // Reset form when modal opens
      resetForm();
    }
  }, [isOpen]);

  // Calculate total from extracted amounts
  const totalFromFiles = extractedAmounts.reduce((sum, amt) => sum + amt, 0);

  function resetForm() {
    setClaimType('reimbursement');
    setCategoryId('');
    setLocationId('');
    setAmount('');
    setDescription('');
    setFiles([]);
    setPreviewUrls([]);
    setExtractedAmounts([]);
    setError(null);
  }

  async function fetchDropdownData() {
    try {
      const { authenticatedFetch } = await import('@/utils/api');
      
      const [categoriesRes, locationsRes] = await Promise.all([
        authenticatedFetch(`${API_BASE_URL}/api/categories`),
        authenticatedFetch(`${API_BASE_URL}/api/locations`)
      ]);

      if (categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategories(data.categories || []);
      }
      if (locationsRes.ok) {
        const data = await locationsRes.json();
        setLocations(Array.isArray(data) ? data : (data.locations || []));
      }
    } catch (err) {
      console.error('Failed to load dropdown data:', err);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const newFiles = e.target.files ? Array.from(e.target.files) : [];
    addFiles(newFiles);
  }

  function addFiles(newFiles: File[]) {
    if (newFiles.length > 0) {
      setFiles(prev => [...prev, ...newFiles]);
      const newUrls = newFiles.map(file => 
        file.type.startsWith('image/') ? URL.createObjectURL(file) : ''
      );
      setPreviewUrls(prev => [...prev, ...newUrls]);
      
      // Mock OCR extraction - in real implementation, this would call backend
      // For now, just add placeholder amounts
      const mockAmounts = newFiles.map(() => 0);
      setExtractedAmounts(prev => [...prev, ...mockAmounts]);
    }
  }

  function removeFile(index: number) {
    setFiles(files => files.filter((_, i) => i !== index));
    setPreviewUrls(urls => urls.filter((_, i) => i !== index));
    setExtractedAmounts(amounts => amounts.filter((_, i) => i !== index));
  }

  function handleDragEnter(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = e.dataTransfer.files ? Array.from(e.dataTransfer.files) : [];
    const validFiles = droppedFiles.filter(file => 
      file.type.startsWith('image/') || file.type === 'application/pdf'
    );
    addFiles(validFiles);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Validation based on claim type
    if (claimType === 'reimbursement') {
      if (!categoryId || files.length === 0) {
        setError('Category and at least one receipt are required for reimbursement claims');
        return;
      }
    } else {
      // Advance
      if (!categoryId || !description) {
        setError('Category and description are required for advance claims');
        return;
      }
      if (files.length === 0 && !amount) {
        setError('Either enter an amount or upload quotations');
        return;
      }
    }

    setLoading(true);

    try {
      const { authenticatedFetch } = await import('@/utils/api');
      const formData = new FormData();
      
      // Add files (receipts or quotations)
      const fileFieldName = claimType === 'reimbursement' ? 'receipts' : 'quotations';
      files.forEach((file) => {
        formData.append(fileFieldName, file);
      });
      
      formData.append('category_id', categoryId);
      if (locationId) formData.append('location_id', locationId);
      if (description) formData.append('description', description);
      
      // Send amount if provided by user (for both claim types)
      if (amount) {
        formData.append('amount', amount);
      }

      const endpoint = claimType === 'advance' 
        ? `${API_BASE_URL}/api/claims/advance`
        : `${API_BASE_URL}/api/claims`;

      const res = await authenticatedFetch(endpoint, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const data = await res.json();
        console.error('Backend error:', data);
        // Handle validation errors
        if (data.detail && Array.isArray(data.detail)) {
          const errorMessages = data.detail.map((err: any) => 
            `${err.loc?.join('.') || 'Field'}: ${err.msg}`
          ).join(', ');
          throw new Error(errorMessages);
        }
        throw new Error(data.detail || data.message || 'Failed to submit claim');
      }

      const result = await res.json();
      console.log('Claim created:', result);
      
      resetForm();
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Submit error:', err);
      const errorMessage = err instanceof Error ? err.message : 
        (typeof err === 'string' ? err : 'Failed to submit claim. Please try again.');
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  const fileLabel = claimType === 'reimbursement' ? 'Receipt Images' : 'Quotation Images';
  const fileRequired = claimType === 'reimbursement';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 rounded-t-2xl">
          <h2 className="text-xl font-bold text-white">Submit New Claim</h2>
          <p className="text-indigo-100 text-sm">Choose claim type and enter details</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Claim Type Toggle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Claim Type <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setClaimType('reimbursement')}
                className={`px-4 py-3 rounded-lg border-2 font-medium transition-all ${
                  claimType === 'reimbursement'
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-indigo-300'
                }`}
              >
                💰 After Pay
                <p className="text-xs font-normal mt-1">Reimbursement</p>
              </button>
              <button
                type="button"
                onClick={() => setClaimType('advance')}
                className={`px-4 py-3 rounded-lg border-2 font-medium transition-all ${
                  claimType === 'advance'
                    ? 'border-purple-600 bg-purple-50 text-purple-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-purple-300'
                }`}
              >
                📋 Before Pay
                <p className="text-xs font-normal mt-1">Advance</p>
              </button>
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

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {fileLabel} {fileRequired && <span className="text-red-500">*</span>}
              {!fileRequired && <span className="text-gray-400">(optional)</span>}
            </label>
            <div 
              className={`border-2 border-dashed rounded-xl p-4 text-center transition-all ${
                isDragging 
                  ? 'border-indigo-500 bg-indigo-50' 
                  : 'border-gray-300 hover:border-indigo-400'
              }`}
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {files.length > 0 && (
                <div className="flex flex-wrap gap-4 justify-center mb-4">
                  {files.map((file, idx) => (
                    <div key={idx} className="relative flex flex-col items-center">
                      {previewUrls[idx] && file.type.startsWith('image/') ? (
                        <div className="relative w-20 h-20 mb-1">
                          <Image 
                            src={previewUrls[idx]} 
                            alt={`File ${idx+1}`} 
                            fill
                            className="object-cover rounded-lg" 
                          />
                        </div>
                      ) : (
                        <span className="text-2xl">📄</span>
                      )}
                      <span className="text-gray-600 text-xs max-w-[80px] truncate">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => removeFile(idx)}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-red-600"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <label className="cursor-pointer block">
                <div className="text-4xl mb-2">📸</div>
                <p className="text-gray-500 font-medium">
                  {files.length > 0 ? 'Add More Files' : 'Drag & drop files here'}
                </p>
                <p className="text-gray-400 text-xs mt-1">
                  or click to browse • JPG, PNG or PDF up to 5MB each
                </p>
                <input
                  type="file"
                  accept="image/*,.pdf"
                  multiple
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Amount (Rs.) {claimType === 'advance' && files.length === 0 && <span className="text-red-500">*</span>}
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="Enter claim amount"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              required={claimType === 'advance' && !files.length}
            />
            {files.length > 0 && (
              <p className="text-sm text-gray-500 mt-1">
                💡 You can enter amount manually or let the backend calculate from {claimType === 'reimbursement' ? 'receipts' : 'quotations'}
              </p>
            )}
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
              Description {claimType === 'advance' ? <span className="text-red-500">*</span> : <span className="text-gray-400">(optional)</span>}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add any additional details..."
              rows={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
              required={claimType === 'advance'}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={() => { resetForm(); onClose(); }}
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
