import { useState, useEffect } from 'react';
import { authenticatedFetch } from '@/utils/api';

interface ActiveFilters {
  status: string;
  employeeId: string;
  unitId: string;
  startDate: string;
  endDate: string;
}

interface ExportClaimsModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationId?: number | null;
  activeFilters: ActiveFilters;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function ExportClaimsModal({ isOpen, onClose, organizationId, activeFilters }: ExportClaimsModalProps) {
  const [format, setFormat] = useState<'csv' | 'xlsx'>('xlsx');
  const [isExporting, setIsExporting] = useState(false);

  async function handleExport() {
    setIsExporting(true);
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      if (activeFilters.startDate) params.append('start_date', activeFilters.startDate);
      if (activeFilters.endDate) params.append('end_date', activeFilters.endDate);
      if (activeFilters.unitId) params.append('unit_id', activeFilters.unitId);
      if (activeFilters.employeeId) params.append('employee_id', activeFilters.employeeId);
      if (activeFilters.status) params.append('status', activeFilters.status);

      const response = await authenticatedFetch(`${API_BASE_URL}/api/claims/export?${params.toString()}`);

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail
          ? (typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail))
          : 'Export failed';
        throw new Error(errorMessage);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `claims_export_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      onClose();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden">
        <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Export Claims</h3>

          <div className="space-y-4">
            {/* Format Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
              <div className="flex gap-4">
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    className="form-radio text-indigo-600"
                    name="format"
                    value="csv"
                    checked={format === 'csv'}
                    onChange={() => setFormat('csv')}
                  />
                  <span className="ml-2">CSV</span>
                </label>
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    className="form-radio text-indigo-600"
                    name="format"
                    value="xlsx"
                    checked={format === 'xlsx'}
                    onChange={() => setFormat('xlsx')}
                  />
                  <span className="ml-2">Excel (.xlsx)</span>
                </label>
              </div>
            </div>

            {/* Info Message */}
            <div className="bg-blue-50 text-blue-700 p-3 rounded-lg text-sm mb-4">
              <p>The export will use the active filters from the Claims page.</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting}
            className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm ${
              isExporting ? 'opacity-75 cursor-not-allowed' : ''
            }`}
          >
            {isExporting ? 'Exporting...' : 'Export'}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={isExporting}
            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
