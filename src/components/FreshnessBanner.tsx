'use client';

import { useState } from 'react';
import { Info, X } from 'lucide-react';

export default function FreshnessBanner() {
    const [visible, setVisible] = useState(true);

    if (!visible) return null;

    return (
        <div className="bg-indigo-900/90 text-indigo-100 px-4 py-2 text-xs font-medium flex items-center justify-between border-b border-indigo-800 backdrop-blur-sm">
            <div className="flex items-center gap-3">
                <span className="bg-indigo-500/20 p-1 rounded text-indigo-300">
                    <Info className="w-3 h-3" />
                </span>
                <div className="flex gap-4">
                    <span>
                        <strong className="text-white">Free-Data Mode:</strong> Intraday limited (1m ≤ ~7d; &lt;1d ≤ ~60d)
                    </span>
                    <span className="hidden sm:inline text-indigo-400">|</span>
                    <span className="hidden sm:inline">
                        <strong className="text-white">Alpha Vantage fallback:</strong> 5/min, 500/day
                    </span>
                </div>
            </div>
            <button
                onClick={() => setVisible(false)}
                className="hover:bg-indigo-800/50 p-1 rounded transition-colors"
            >
                <X className="w-3 h-3" />
            </button>
        </div>
    );
}
