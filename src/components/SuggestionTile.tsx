import { useState } from 'react';
import { QuestionSuggestion } from '@/lib/types';
import ConfidenceBadge from './ConfidenceBadge';
import CitationChip from './CitationChip';
import { CheckCircle2, Circle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import clsx from 'clsx';

interface SuggestionTileProps {
    question: string;
    questionId: string;
    suggestion: QuestionSuggestion;
    onAccept: () => void;
    onOverride: (value: 'Yes' | 'No' | 'Unsure') => void;
    onSkip: () => void;
    userAnswer?: 'Yes' | 'No' | 'Unsure';
    disabled: boolean;
    projectedImpact: number;
}

export default function SuggestionTile({
    question,
    questionId,
    suggestion,
    onAccept,
    onOverride,
    onSkip,
    userAnswer,
    disabled,
    projectedImpact
}: SuggestionTileProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const hasAccepted = userAnswer !== undefined;
    const isLowConfidence = suggestion.confidence === 'Low';

    return (
        <div
            className={clsx(
                'p-5 rounded-xl border transition-all relative bg-white dark:bg-gray-800',
                hasAccepted
                    ? 'border-indigo-200 dark:border-indigo-800'
                    : 'border-indigo-100 dark:border-gray-700',
                'hover:border-indigo-300 dark:hover:border-indigo-600 shadow-sm'
            )}
        >
            {/* Projected Impact Badge - Top Right */}
            {projectedImpact !== 0 && !hasAccepted && (
                <div className={clsx(
                    'absolute top-5 right-5 px-2.5 py-1 rounded-md text-xs font-bold',
                    projectedImpact > 0
                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                        : 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'
                )}>
                    {projectedImpact > 0 ? '+' : ''}{projectedImpact}
                </div>
            )}

            {/* Header */}
            <div className="mb-4 pr-12">
                <p className="text-base font-medium text-gray-900 dark:text-gray-100 mb-3 leading-snug">
                    {question}
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Model suggestion:</span>
                    <span className="text-sm font-bold text-indigo-600 dark:text-indigo-400">
                        {suggestion.rec}
                    </span>
                    <ConfidenceBadge confidence={suggestion.confidence} />
                </div>
            </div>

            {/* Low Confidence Warning */}
            {isLowConfidence && !hasAccepted && (
                <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-700 dark:text-amber-300 leading-relaxed">
                        Evidence is sparse or outdated. Please verify independently.
                    </p>
                </div>
            )}

            {/* Evidence Toggle */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-1.5 text-xs font-bold text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400 mb-4 transition-colors"
            >
                {isExpanded ? (
                    <>Hide details <ChevronUp className="w-3 h-3" /></>
                ) : (
                    <>View analysis details <ChevronDown className="w-3 h-3" /></>
                )}
            </button>

            {/* Collapsible Content */}
            {isExpanded && (
                <div className="animate-in fade-in slide-in-from-top-2 duration-200">
                    {/* Reasons */}
                    <div className="mb-4">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Why:</p>
                        <ul className="space-y-2">
                            {suggestion.reasons.map((reason, idx) => (
                                <li key={idx} className="text-sm text-gray-600 dark:text-gray-300 flex items-start gap-2.5 leading-relaxed">
                                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0 mt-2" />
                                    <span>{reason}</span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Citations */}
                    <div className="mb-5">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Sources:</p>
                        <div className="flex flex-wrap gap-2">
                            {suggestion.citations.map((citation, idx) => (
                                <CitationChip key={idx} citation={citation} index={idx} />
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Actions */}
            {!disabled && !hasAccepted && (
                <div className="flex items-center gap-3">
                    <button
                        onClick={onAccept}
                        className="flex-1 py-2.5 px-4 rounded-lg text-sm font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm hover:shadow-md"
                    >
                        Accept
                    </button>
                    <button
                        onClick={() => onOverride('Yes')}
                        className="py-2.5 px-4 rounded-lg text-sm font-bold bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border border-gray-300 dark:border-gray-600"
                    >
                        Override: Yes
                    </button>
                    <button
                        onClick={() => onOverride('No')}
                        className="py-2.5 px-4 rounded-lg text-sm font-bold bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border border-gray-300 dark:border-gray-600"
                    >
                        Override: No
                    </button>
                    <button
                        onClick={onSkip}
                        className="px-4 py-2.5 rounded-lg text-sm font-bold text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                    >
                        Skip
                    </button>
                </div>
            )}

            {/* User Answer Display */}
            {hasAccepted && (
                <div className="flex items-center justify-between p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-100 dark:border-indigo-800">
                    <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            You answered: <span className="font-bold text-indigo-700 dark:text-indigo-300">{userAnswer}</span>
                        </span>
                    </div>
                    {!disabled && (
                        <button
                            onClick={() => {
                                // Clear the user answer to show action buttons again
                                onOverride(undefined as any);
                            }}
                            className="px-3 py-1.5 rounded-lg text-xs font-bold text-indigo-600 hover:bg-indigo-100 dark:text-indigo-400 dark:hover:bg-indigo-900/40 transition-colors"
                        >
                            Edit
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
