'use client'; 

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application Error:', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] p-6 text-center">
      <div className="bg-red-50 text-red-900 p-8 rounded-2xl max-w-lg shadow-sm border border-red-100">
        <h2 className="text-2xl font-bold mb-4">Something went wrong!</h2>
        <p className="text-gray-600 mb-6">
          {error.message || "An unexpected error occurred. Please try again."}
        </p>
        <button
          onClick={
            // Attempt to recover by trying to re-render the segment
            () => reset()
          }
          className="px-6 py-2.5 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-colors shadow-sm"
        >
          Try again
        </button>
        <div className="mt-8 pt-6 border-t border-red-100">
             <p className="text-xs text-gray-400">
                If this persists, please check your internet connection or contact support.
             </p>
        </div>
      </div>
    </div>
  );
}
