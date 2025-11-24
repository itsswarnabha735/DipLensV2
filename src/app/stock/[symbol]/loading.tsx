import { Loader2 } from 'lucide-react';

export default function Loading() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="relative flex items-center justify-center mb-4">
                <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full animate-pulse w-16 h-16"></div>
                <div className="relative bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700">
                    <Loader2 className="w-8 h-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
                </div>
            </div>
            <div className="space-y-2 text-center">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">Analyzing Market Data</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 animate-pulse">
                    Crunching the numbers...
                </p>
            </div>
        </div>
    );
}
