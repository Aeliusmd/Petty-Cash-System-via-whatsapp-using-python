import Link from 'next/link';

interface RecentClaim {
  claim_number: string;
  created_at: string;
  employee_name: string;
  category_name: string;
  final_amount: number;
  status_code: string;
}

interface RecentActivityListProps {
  claims: RecentClaim[];
}

export default function RecentActivityList({ claims }: RecentActivityListProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-6 border-b border-gray-100 flex justify-between items-center">
        <h3 className="font-bold text-gray-800">Recent Claims</h3>
        <Link href="/claims" className="text-indigo-600 text-sm font-medium hover:text-indigo-800">
          View All →
        </Link>
      </div>

      {/* Desktop Table View (Hidden on mobile) */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-gray-500 uppercase bg-gray-50">
            <tr>
              <th className="px-6 py-3">Claim</th>
              <th className="px-6 py-3">Employee</th>
              <th className="px-6 py-3">Amount</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Date</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_number} className="bg-white border-b hover:bg-gray-50">
                <td className="px-6 py-4 font-medium text-gray-900">
                  {claim.claim_number}
                  <span className="block text-xs text-gray-400 font-normal">{claim.category_name}</span>
                </td>
                <td className="px-6 py-4">{claim.employee_name}</td>
                <td className="px-6 py-4">LKR {(claim.final_amount || 0).toLocaleString()}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    claim.status_code === 'APPROVED' ? 'bg-green-100 text-green-800' :
                    claim.status_code === 'REJECTED' ? 'bg-red-100 text-red-800' :
                    'bg-orange-100 text-orange-800'
                  }`}>
                    {claim.status_code}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-500">
                  {new Date(claim.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {claims.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                  No recent claims found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View (Hidden on desktop) */}
      <div className="md:hidden">
        {claims.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No recent claims found
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {claims.map((claim) => (
              <div key={claim.claim_number} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <span className="text-sm font-semibold text-gray-900 block">{claim.claim_number}</span>
                    <span className="text-xs text-gray-500">{claim.employee_name}</span>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    claim.status_code === 'APPROVED' ? 'bg-green-100 text-green-800' :
                    claim.status_code === 'REJECTED' ? 'bg-red-100 text-red-800' :
                    'bg-orange-100 text-orange-800'
                  }`}>
                    {claim.status_code}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <div className="flex flex-col">
                    <span className="text-gray-600 text-xs uppercase tracking-wider">Amount</span>
                    <span className="font-medium text-gray-900">LKR {(claim.final_amount || 0).toLocaleString()}</span>
                  </div>
                   <div className="flex flex-col items-end">
                    <span className="text-gray-600 text-xs uppercase tracking-wider">Date</span>
                    <span className="text-gray-700">{new Date(claim.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-gray-50 flex justify-between items-center">
                   <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded inline-block">
                     {claim.category_name}
                   </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
