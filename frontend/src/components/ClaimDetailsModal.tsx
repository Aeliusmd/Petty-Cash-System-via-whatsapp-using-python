'use client';

import { useEffect, useState } from 'react';
import { authenticatedFetch } from '@/utils/api';
import Image from 'next/image';

interface Receipt {
  id: number;
  claim_id: number;
  file_path: string;
  file_name: string;
  file_type: string;
  file_size: number;
  ocr_amount: number | null;
  ocr_raw_text: string | null;
  vendor: string | null;
  uploaded_at: string;
}

interface Claim {
  id: number;
  claim_number: string;
  employee_name: string;
  employee_code: string;
  category_name: string;
  category_code: string;
  location_name: string | null;
  status_code: string;
  status_name: string;
  claim_type: string;
  claim_date: string;
  duration_days: number;
  user_amount: number | null;
  system_amount: number | null;
  final_amount: number | null;
  description: string | null;
  rejection_reason: string | null;
  appeal_count: number | null;
  created_at: string;
}

interface ClaimDetailsModalProps {
  claim: Claim;
  isOpen: boolean;
  onClose: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

function formatCurrency(amount: number | null): string {
  if (amount === null || amount === undefined) return 'Rs.0';
  return `Rs.${amount.toLocaleString()}`;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '-';

  return date.toLocaleDateString('en-LK', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'PENDING': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'APPROVED': return 'bg-green-100 text-green-800 border-green-200';
    case 'REJECTED': return 'bg-red-100 text-red-800 border-red-200';
    case 'APPEALED': return 'bg-purple-100 text-purple-800 border-purple-200';
    default: return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

function getCategoryIcon(code: string): string {
  switch (code) {
    case 'BATTA': return '🏷️';
    case 'FUEL': return '⛽';
    case 'ACCOM': return '🏨';
    case 'SUNDRY': return '📦';
    default: return '📋';
  }
}

export default function ClaimDetailsModal({ claim, isOpen, onClose }: ClaimDetailsModalProps) {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  
  // Appeal state
  const [showAppealForm, setShowAppealForm] = useState(false);
  const [appealNotes, setAppealNotes] = useState('');
  const [appealSubmitting, setAppealSubmitting] = useState(false);
  const [appealError, setAppealError] = useState<string | null>(null);
  const [appealReceipts, setAppealReceipts] = useState<File[]>([]);
  const [appealPreviewUrls, setAppealPreviewUrls] = useState<string[]>([]);
  const [appealDragging, setAppealDragging] = useState(false);

  useEffect(() => {
    if (isOpen && claim) {
      fetchReceipts();
    }
  }, [isOpen, claim]);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (selectedImage) {
          setSelectedImage(null);
        } else {
          onClose();
        }
      }
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEsc);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      document.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, selectedImage, onClose]);

  async function fetchReceipts() {
    setLoading(true);
    try {
      // Use authenticatedFetch to include ngrok-skip-browser-warning header
      const res = await authenticatedFetch(`${API_BASE_URL}/api/claims/${claim.id}/receipts`);
      if (res.ok) {
        const data = await res.json();
        setReceipts(data.receipts || []);
      }
    } catch (err) {
      console.error('Failed to fetch receipts:', err);
    } finally {
      setLoading(false);
    }
  }

  function getFileUrl(receipt: Receipt): string {
    // file_path now stores only the filename (e.g., "uuid.jpeg")
    // No need for complex path extraction
    return `${API_BASE_URL}/api/receipts/${receipt.file_path}`;
  }

  function isImageFile(receipt: Receipt): boolean {
    const fileType = receipt.file_type?.toLowerCase() || '';
    const fileName = receipt.file_name?.toLowerCase() || '';
    return fileType.includes('image') || 
           fileName.endsWith('.jpg') || 
           fileName.endsWith('.jpeg') || 
           fileName.endsWith('.png') || 
           fileName.endsWith('.gif');
  }

  function isPdfFile(receipt: Receipt): boolean {
    const fileType = receipt.file_type?.toLowerCase() || '';
    const fileName = receipt.file_name?.toLowerCase() || '';
    return fileType.includes('pdf') || fileName.endsWith('.pdf');
  }

  async function submitAppeal() {
    if (!appealNotes.trim()) {
      setAppealError('Please provide a reason for your appeal');
      return;
    }

    setAppealSubmitting(true);
    setAppealError(null);

    try {
      // Use FormData to support file uploads
      const formData = new FormData();
      formData.append('notes', appealNotes);
      
      // Append all receipt files
      appealReceipts.forEach((file) => {
        formData.append('receipts', file);
      });

      const res = await authenticatedFetch(
        `${API_BASE_URL}/api/claims/${claim.id}/appeal`,
        {
          method: 'POST',
          body: formData  // Send FormData instead of JSON
        }
      );

      if (res.ok) {
        // Refresh receipts to ensure they display after appeal
        await fetchReceipts();
        
        // Close appeal form and reset state
        setShowAppealForm(false);
        setAppealNotes('');
        setAppealReceipts([]);
        setAppealPreviewUrls([]);
        
        // Show success message
        alert('✅ Appeal submitted successfully! Your manager will review it.');
        
        // Close modal
        onClose();
        
        // Reload page to refresh claim status
        window.location.reload();
      } else {
        const data = await res.json();
        setAppealError(data.detail || 'Failed to submit appeal');
      }
    } catch (err) {
      setAppealError('Failed to submit appeal. Please try again.');
      console.error('Appeal submission error:', err);
    } finally {
      setAppealSubmitting(false);
    }
  }

  function handleAppealFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length > 0) {
      setAppealReceipts(prev => [...prev, ...files]);
      const newUrls = files.map(file => 
        file.type.startsWith('image/') ? URL.createObjectURL(file) : ''
      );
      setAppealPreviewUrls(prev => [...prev, ...newUrls]);
    }
  }

  function removeAppealReceipt(index: number) {
    setAppealReceipts(files => files.filter((_, i) => i !== index));
    setAppealPreviewUrls(urls => urls.filter((_, i) => i !== index));
  }

  function handleAppealDragEnter(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setAppealDragging(true);
  }

  function handleAppealDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
  }

  function handleAppealDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setAppealDragging(false);
  }

  function handleAppealDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setAppealDragging(false);

    const files = e.dataTransfer.files ? Array.from(e.dataTransfer.files) : [];
    if (files.length > 0) {
      setAppealReceipts(prev => [...prev, ...files]);
      const newUrls = files.map(file => 
        file.type.startsWith('image/') ? URL.createObjectURL(file) : ''
      );
      setAppealPreviewUrls(prev => [...prev, ...newUrls]);
    }
  }

  if (!isOpen) return null;

  return (
    <>
      {/* Modal Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div 
            className="relative bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between rounded-t-2xl z-10">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{getCategoryIcon(claim.category_code)}</span>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">{claim.claim_number}</h2>
                  <p className="text-sm text-gray-600">{claim.category_name} Claim</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-gray-100 rounded-full"
                aria-label="Close"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="p-6 space-y-6">
              {/* Claim Info Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Employee Info */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <span>👤</span> Employee
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Name</dt>
                      <dd className="font-medium text-gray-800">{claim.employee_name}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Code</dt>
                      <dd className="font-medium text-gray-800">{claim.employee_code}</dd>
                    </div>
                  </dl>
                </div>

                {/* Amount Info */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <span>💰</span> Amount
                  </h3>
                  <dl className="space-y-2 text-sm">
                    {claim.user_amount && (
                      <div className="flex justify-between">
                        <dt className="text-gray-600">User Amount</dt>
                        <dd className="font-medium text-gray-800">{formatCurrency(claim.user_amount)}</dd>
                      </div>
                    )}
                    {claim.system_amount && (
                      <div className="flex justify-between">
                        <dt className="text-gray-600">System Amount</dt>
                        <dd className="font-medium text-gray-800">{formatCurrency(claim.system_amount)}</dd>
                      </div>
                    )}
                    <div className="flex justify-between pt-2 border-t">
                      <dt className="text-gray-700 font-medium">Final Amount</dt>
                      <dd className="font-bold text-lg text-indigo-600">
                        {formatCurrency(claim.final_amount || claim.system_amount || claim.user_amount)}
                      </dd>
                    </div>
                  </dl>
                </div>

                {/* Claim Details */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <span>📋</span> Details
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Type</dt>
                      <dd className="font-medium text-gray-800 capitalize">{claim.claim_type}</dd>
                    </div>
                    {claim.location_name && (
                      <div className="flex justify-between">
                        <dt className="text-gray-600">Location</dt>
                        <dd className="font-medium text-gray-800">{claim.location_name}</dd>
                      </div>
                    )}
                    {claim.duration_days > 1 && (
                      <div className="flex justify-between">
                        <dt className="text-gray-600">Duration</dt>
                        <dd className="font-medium text-gray-800">{claim.duration_days} days</dd>
                      </div>
                    )}
                  </dl>
                </div>

                {/* Status & Date */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <span>🕐</span> Status & Date
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between items-center">
                      <dt className="text-gray-600">Status</dt>
                      <dd>
                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(claim.status_code)}`}>
                          {claim.status_name}
                        </span>
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Claim Date</dt>
                      <dd className="font-medium text-gray-800">{formatDate(claim.claim_date)}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Submitted</dt>
                      <dd className="font-medium text-gray-800">{formatDate(claim.created_at)}</dd>
                    </div>
                  </dl>
                </div>
              </div>

              {/* Description */}
              {claim.description && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                    <span>📝</span> Description
                  </h3>
                  <p className="text-gray-700 text-sm whitespace-pre-wrap">{claim.description}</p>
                </div>
              )}

              {/* Rejection Reason + Appeal Button */}
              {claim.rejection_reason && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-red-800 flex items-center gap-2">
                      <span>❌</span> Rejection Reason
                    </h3>
                    {claim.status_code === 'REJECTED' && (
                      <button
                        onClick={() => setShowAppealForm(true)}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium flex items-center gap-2"
                      >
                        <span>🔄</span> Appeal This Decision
                      </button>
                    )}
                  </div>
                  <p className="text-red-700 text-sm">{claim.rejection_reason}</p>
                </div>
              )}

              {/* Receipts Section */}
              <div className="border-t pt-6">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <span>📎</span> Attachments ({receipts.length})
                </h3>
                
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                  </div>
                ) : receipts.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <p>No attachments found for this claim</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Images Grid */}
                    {receipts.filter(isImageFile).length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-3">Images</h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          {receipts.filter(isImageFile).map((receipt) => (
                            <div 
                              key={receipt.id}
                              className="relative aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-indigo-500 transition-all"
                              onClick={() => setSelectedImage(getFileUrl(receipt))}
                            >
                              <img
                                src={getFileUrl(receipt)}
                                alt={receipt.file_name}
                                className="w-full h-full object-cover"
                              />
                              {(receipt.ocr_amount || receipt.vendor) && (
                                <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-70 text-white text-xs p-2">
                                  {receipt.vendor && <div>Vendor: {receipt.vendor}</div>}
                                  {receipt.ocr_amount && <div>Amount: {formatCurrency(receipt.ocr_amount)}</div>}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* PDFs List */}
                    {receipts.filter(isPdfFile).length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-3">PDF Documents</h4>
                        <div className="space-y-2">
                          {receipts.filter(isPdfFile).map((receipt) => (
                            <a
                              key={receipt.id}
                              href={getFileUrl(receipt)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                            >
                              <span className="text-2xl">📄</span>
                              <div className="flex-1">
                                <p className="font-medium text-gray-800 text-sm">{receipt.file_name}</p>
                                <p className="text-xs text-gray-500">
                                  {(receipt.file_size / 1024).toFixed(1)} KB • {formatDate(receipt.uploaded_at)}
                                </p>
                              </div>
                              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Appeal Form Modal */}
      {showAppealForm && (
        <>
          <div 
            className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm z-50"
            onClick={() => setShowAppealForm(false)}
          />
          <div className="fixed inset-0 z-[60] overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4">
              <div 
                className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full p-6"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                    <span>🔄</span> Appeal Rejection
                  </h3>
                  <button
                    onClick={() => setShowAppealForm(false)}
                    className="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-gray-100 rounded-full"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <p className="text-gray-600 text-sm mb-4">
                  Explain why you believe this claim should be reconsidered. Your manager will review your appeal.
                </p>

                {/* Error Message */}
                {appealError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                    {appealError}
                  </div>
                )}

                {/* Appeal Notes Textarea */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Appeal Reason *
                  </label>
                  <textarea
                    value={appealNotes}
                    onChange={(e) => setAppealNotes(e.target.value)}
                    placeholder="Explain why this claim should be approved..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                    rows={4}
                    disabled={appealSubmitting}
                  />
                </div>

                {/* Receipt Upload Section */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Additional Receipts (Optional)
                  </label>
                  
                  {/* File Preview Grid */}
                  {appealReceipts.length > 0 && (
                    <div className="flex flex-wrap gap-3 mb-3">
                      {appealReceipts.map((file, idx) => (
                        <div key={idx} className="relative">
                          {appealPreviewUrls[idx] && file.type.startsWith('image/') ? (
                            <img 
                              src={appealPreviewUrls[idx]} 
                              alt={`Receipt ${idx+1}`} 
                              className="w-20 h-20 object-cover rounded-lg border-2 border-gray-200" 
                            />
                          ) : (
                            <div className="w-20 h-20 flex items-center justify-center bg-gray-100 rounded-lg border-2 border-gray-200">
                              <span className="text-2xl">📄</span>
                            </div>
                          )}
                          <button
                            type="button"
                            onClick={() => removeAppealReceipt(idx)}
                            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600 shadow-md"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* File Input */}
                  <label className="cursor-pointer block">
                    <div 
                      className={`border-2 border-dashed rounded-lg p-4 transition-colors text-center ${
                        appealDragging 
                          ? 'border-indigo-500 bg-indigo-50' 
                          : 'border-gray-300 hover:border-indigo-400'
                      }`}
                      onDragEnter={handleAppealDragEnter}
                      onDragOver={handleAppealDragOver}
                      onDragLeave={handleAppealDragLeave}
                      onDrop={handleAppealDrop}
                    >
                      <div className="text-2xl mb-1">📎</div>
                      <p className="text-sm text-gray-600">
                        {appealReceipts.length > 0 ? 'Add More Files' : 'Drag & drop files here'}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">or click to browse • JPG, PNG or PDF</p>
                    </div>
                    <input
                      type="file"
                      accept="image/*,.pdf"
                      multiple
                      onChange={handleAppealFileChange}
                      className="hidden"
                      disabled={appealSubmitting}
                    />
                  </label>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowAppealForm(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                    disabled={appealSubmitting}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={submitAppeal}
                    disabled={appealSubmitting || !appealNotes.trim()}
                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {appealSubmitting ? 'Submitting...' : 'Submit Appeal'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Image Lightbox */}
      {selectedImage && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-90 z-[60] flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <button
            onClick={() => setSelectedImage(null)}
            className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors"
            aria-label="Close"
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <img
            src={selectedImage}
            alt="Receipt"
            className="max-w-full max-h-full object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
}
