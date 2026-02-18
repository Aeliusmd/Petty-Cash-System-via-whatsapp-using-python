import { useState, useEffect } from 'react';
import { authenticatedFetch } from '@/utils/api';

interface Unit {
  id: number;
  name: string;
}

interface Employee {
  id: number;
  name: string;
  employee_code: string;
}

interface ExportClaimsModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationId?: number | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4101';

export default function ExportClaimsModal({ isOpen, onClose, organizationId }: ExportClaimsModalProps) {
  const [format, setFormat] = useState<'csv' | 'xlsx'>('xlsx');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [unitId, setUnitId] = useState<string>('');
  const [employeeId, setEmployeeId] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [isExporting, setIsExporting] = useState(false);
  const [units, setUnits] = useState<Unit[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchUnits();
    }
  }, [isOpen]);

  // When department changes, reload employees
  useEffect(() => {
    setEmployeeId(''); // reset employee when department changes
    fetchEmployeesByUnit(unitId || null);
  }, [unitId]);

  useEffect(() => {
    if (isOpen) {
      fetchUnits();
      fetchEmployeesByUnit(null); // load all employees initially
    }
  }, [isOpen]);

  async function fetchUnits() {
    try {
      const url = organizationId
        ? `${API_BASE_URL}/api/units?organization_id=${organizationId}`
        : `${API_BASE_URL}/api/units`;
      const res = await authenticatedFetch(url);
      if (res.ok) {
        const data = await res.json();
        setUnits(data.units || []);
      }
    } catch (err) {
      console.error('Failed to fetch units', err);
    }
  }

  async function fetchEmployeesByUnit(unitId: string | null) {
    setLoadingEmployees(true);
    try {
      const url = unitId
        ? `${API_BASE_URL}/api/employees/?unit_id=${unitId}`
        : `${API_BASE_URL}/api/employees/`;
      const res = await authenticatedFetch(url);
      if (res.ok) {
        const data = await res.json();
        setEmployees(data.employees || []);
      }
    } catch (err) {
      console.error('Failed to fetch employees', err);
    } finally {
      setLoadingEmployees(false);
    }
  }

  async function handleExport() {
    setIsExporting(true);
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (unitId) params.append('unit_id', unitId);
      if (employeeId) params.append('employee_id', employeeId);
      if (status) params.append('status', status);

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

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>
            </div>

            {/* Department */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Department</label>
              <select
                value={unitId}
                onChange={(e) => setUnitId(e.target.value)}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Departments</option>
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Employee */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Employee
                {loadingEmployees && (
                  <span className="ml-2 text-xs text-gray-400">Loading...</span>
                )}
              </label>
              <select
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                disabled={loadingEmployees}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:bg-gray-50 disabled:text-gray-400"
              >
                <option value="">All Employees</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.name} ({emp.employee_code})
                  </option>
                ))}
              </select>
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Statuses</option>
                <option value="PENDING">Pending</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
                <option value="APPEALED">Appealed</option>
              </select>
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
