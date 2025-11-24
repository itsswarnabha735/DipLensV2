'use client';

import { FundamentalsSuggestionResponse } from '@/lib/types';
import CitationChip from './CitationChip';
import { FileText, AlertTriangle } from 'lucide-react';

interface SummaryCardProps {
    suggestion: FundamentalsSuggestionResponse;
}

export default function SummaryCard({ suggestion }: SummaryCardProps) {
    // Collect all unique citations
    const allCitations = [
        ...suggestion.q1.citations,
        ...suggestion.q2.citations,
        ...suggestion.q3.citations,
        ...suggestion.q4.citations
    ];

    // Deduplicate by URL
    const uniqueCitations = allCitations.filter(
        (citation, index, self) =>
            index === self.findIndex(c => c.url === citation.url)
    );

    const hasLowConfidence = [
        suggestion.q1.confidence,
        suggestion.q2.confidence,
        suggestion.q3.confidence,
        suggestion.q4.confidence
    ].some(c => c === 'Low');

    const formatTimestamp = (timestamp: string) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return 'Unknown';
        }
    };

    return (
        <div className="p-5 rounded-xl bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 border border-indigo-200 dark:border-indigo-800">
            {/* Header */}
            <div className="flex items-start gap-3 mb-4">
                <div className="p-2 bg-indigo-500 rounded-lg">
                    <FileText className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                    <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-1">
                        LLM-Generated Summary
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        Generated: {formatTimestamp(suggestion.generated_at)}
                    </p>
                </div>
            </div>

            {/* Summary Text */}
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-4">
                {suggestion.summary}
            </p>

            {/* Low Confidence Warning */}
            {hasLowConfidence && (
                <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <p className="text-xs font-medium text-amber-800 dark:text-amber-300 mb-1">
                            Uncertainty Noted
                        </p>
                        <p className="text-xs text-amber-700 dark:text-amber-400">
                            Some questions have low confidence due to limited or outdated information. Consider additional research before acting.
                        </p>
                    </div>
                </div>
            )}

            {/* All Citations */}
            <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    All sources ({uniqueCitations.length}):
                </p>
                <div className="flex flex-wrap gap-2">
                    {uniqueCitations.map((citation, idx) => (
                        <CitationChip key={idx} citation={citation} index={idx} />
                    ))}
                </div>
            </div>

            {/* Disclaimer */}
            <div className="mt-4 pt-3 border-t border-indigo-200 dark:border-indigo-800">
                <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                    Automated, grounded suggestions for education. You decide. Not investment advice.
                </p>
            </div>
        </div>
    );
}
