'use client';
 
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div className="flex flex-col items-center justify-center min-h-screen p-6 text-center bg-gray-50">
           <div className="bg-white p-10 rounded-3xl shadow-xl max-w-lg">
                <h2 className="text-3xl font-bold mb-4 text-gray-800">Critical Error</h2>
                <p className="text-gray-600 mb-8">
                    A critical system error occurred. We apologize for the inconvenience.
                </p>
                <div className="bg-gray-100 p-4 rounded-xl mb-8 overflow-auto max-h-40 text-left">
                     <code className="text-xs text-red-600 font-mono">
                        {error.message}
                     </code>
                </div>
                <button
                    onClick={() => reset()}
                    className="px-8 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
                >
                    Reload Application
                </button>
           </div>
        </div>
      </body>
    </html>
  );
}
