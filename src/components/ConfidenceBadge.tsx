'use client';

import { HelpCircle } from 'lucide-react';
import clsx from 'clsx';

interface ConfidenceBadgeProps {
    confidence: 'High' | 'Medium' | 'Low';
    showTooltip?: boolean;
}

export default function ConfidenceBadge({ confidence, showTooltip = true }: ConfidenceBadgeProps) {
    const getStyles = () => {
        switch (confidence) {
            case 'High':
                return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
            case 'Medium':
                return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800';
            case 'Low':
                return 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800';
        }
    };

    const getTooltipText = () => {
        switch (confidence) {
            case 'High':
                return '≥2 recent, consistent sources with no conflicts';
            case 'Medium':
                return 'Some evidence, minor conflicts or stale sources';
            case 'Low':
                return 'Sparse, stale, or conflicting evidence';
        }
    };

    return (
        <div className="relative inline-flex items-center group">
            <span
                className={clsx(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold border',
                    getStyles()
                )}
            >
                {confidence}
                {showTooltip && <HelpCircle className="w-3 h-3" />}
            </span>

            {showTooltip && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 w-48 text-center z-10">
                    {getTooltipText()}
                    <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1">
                        <div className="border-4 border-transparent border-t-gray-900 dark:border-t-gray-800"></div>
                    </div>
                </div>
            )}
        </div>
    );
}
