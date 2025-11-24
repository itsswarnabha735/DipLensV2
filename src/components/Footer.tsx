'use client';

import { AlertTriangle } from 'lucide-react';

export default function Footer() {
    return (
        <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 mt-12 py-8">
            <div className="max-w-7xl mx-auto px-4 md:px-8">
                <div className="flex flex-col md:flex-row justify-between items-start gap-6">
                    <div className="max-w-md">
                        <h3 className="font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 text-yellow-500" /> Disclaimer
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                            DipLens is an educational tool for analyzing market dips. It does not provide investment advice, recommendations, or tips.
                            All scores and signals are generated based on technical rules and user inputs.
                            Stock market investments are subject to market risks. Please consult a SEBI registered financial advisor before making any investment decisions.
                        </p>
                    </div>

                    <div className="text-xs text-gray-500 dark:text-gray-400">
                        <p>&copy; {new Date().getFullYear()} DipLens v2. All rights reserved.</p>
                        <p className="mt-1">Data provided by Yahoo Finance (Delayed).</p>
                    </div>
                </div>
            </div>
        </footer>
    );
}
