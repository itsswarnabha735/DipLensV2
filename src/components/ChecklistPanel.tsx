'use client';

import { useState, useEffect } from 'react';
import { PreScore, FinalScore, AllocationBand, FundamentalsSuggestionResponse } from '@/lib/types';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { CheckCircle2, Save, Lock, Loader2, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import SuggestionTile from './SuggestionTile';
import SummaryCard from './SummaryCard';

interface ChecklistPanelProps {
    preScore: PreScore;
    symbol: string;
    questions?: Array<{ id: string; text: string; points: number }>;
}

export default function ChecklistPanel({ preScore, symbol, questions: propQuestions }: ChecklistPanelProps) {
    const [answers, setAnswers] = useState<Record<string, 'Yes' | 'No' | 'Unsure'>>({});
    const [logged, setLogged] = useState(false);
    const [loading, setLoading] = useState(false);
    const [finalScoreData, setFinalScoreData] = useState<any>(null);

    // LLM Suggestions State
    const [suggestions, setSuggestions] = useState<FundamentalsSuggestionResponse | null>(null);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
    const [showSuggestions, setShowSuggestions] = useState(true);

    const addJournalEntry = useAppStore((state) => state.addJournalEntry);
    const quotes = useAppStore((state) => state.quotes);

    const defaultQuestions = [
        { id: 'q1_earnings', text: 'Is the dip primarily macro/sector‑driven (not company‑specific)?', points: 2 },
        { id: 'q2_balance_sheet', text: 'Are revenue and profit broadly intact in the latest results?', points: 2 },
        { id: 'q3_moat', text: 'Any negative guidance or key mgmt exits recently?', points: 2 },
        { id: 'q4_management', text: 'Is the stock near horizontal support you recognize?', points: 2 },
    ];

    const questions = propQuestions || defaultQuestions;

    // Fetch LLM suggestions on mount
    useEffect(() => {
        const fetchSuggestions = async () => {
            setLoadingSuggestions(true);
            setSuggestionsError(null);

            try {
                const data = await api.getFundamentalsSuggestions(symbol);
                setSuggestions(data);
            } catch (error) {
                console.error('Failed to fetch fundamentals suggestions:', error);
                setSuggestionsError('Could not load AI suggestions. You can still answer manually.');
            } finally {
                setLoadingSuggestions(false);
            }
        };

        if (symbol && !logged) {
            fetchSuggestions();
        }
    }, [symbol, logged]);

    const handleAnswer = (id: string, answer: 'Yes' | 'No' | 'Unsure') => {
        if (logged) return;
        setAnswers(prev => ({ ...prev, [id]: answer }));
    };

    const handleAcceptSuggestion = (questionId: string, suggestion: string) => {
        if (logged) return;
        // Map suggestion to Yes/No/Unsure
        let answer: 'Yes' | 'No' | 'Unsure' = 'Unsure';

        // Q1: Macro/Sector = Yes, CompanySpecific = No, Unknown = Unsure
        if (questionId === 'q1_earnings') {
            if (suggestion === 'Macro' || suggestion === 'Sector') answer = 'Yes';
            else if (suggestion === 'CompanySpecific') answer = 'No';
            else answer = 'Unsure';
        }
        // Q2: Yes = Yes, No = No, Unsure = Unsure
        else if (questionId === 'q2_balance_sheet') {
            if (suggestion === 'Yes') answer = 'Yes';
            else if (suggestion === 'No') answer = 'No';
            else answer = 'Unsure';
        }
        // Q3: NoneObserved = Yes, NegativeObserved = No, Unsure = Unsure
        else if (questionId === 'q3_moat') {
            if (suggestion === 'NoneObserved') answer = 'Yes';
            else if (suggestion === 'NegativeObserved') answer = 'No';
            else answer = 'Unsure';
        }
        // Q4: LikelySupport = Yes, NotNear = No, Unsure = Unsure
        else if (questionId === 'q4_management') {
            if (suggestion === 'LikelySupport') answer = 'Yes';
            else if (suggestion === 'NotNear') answer = 'No';
            else answer = 'Unsure';
        }

        setAnswers(prev => ({ ...prev, [questionId]: answer }));
    };

    const allAnswered = questions.every(q => answers[q.id]);

    const handleLogDecision = async () => {
        if (!allAnswered) return;
        setLoading(true);

        try {
            const checklistPayload = {
                q1_earnings: answers['q1_earnings'].toLowerCase(),
                q2_balance_sheet: answers['q2_balance_sheet'].toLowerCase(),
                q3_moat: answers['q3_moat'].toLowerCase(),
                q4_management: answers['q4_management'].toLowerCase(),
            };

            const result = await api.submitChecklist(symbol, checklistPayload);
            setFinalScoreData(result);

            const quote = quotes[symbol];
            const price = quote ? quote.price : 0;

            addJournalEntry({
                id: crypto.randomUUID(),
                symbol,
                timestamp: Date.now(),
                action: result.total_score >= 14 ? 'Buy' : result.total_score >= 10 ? 'Wait' : 'Skip',
                price,
                preScore: result.pre_score,
                finalScore: result.total_score,
                allocationBand: result.band as AllocationBand,
                notes: `Checklist completed. Band: ${result.band}`
            });

            setLogged(true);
        } catch (error) {
            console.error("Failed to submit checklist:", error);
            alert("Failed to submit checklist. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const getBand = (score: number) => {
        if (score >= 14) return 'High Conviction';
        if (score >= 11) return 'Strong';
        if (score >= 8) return 'Moderate';
        if (score >= 6) return 'Weak';
        return 'Skip';
    };

    const bandColor = (band: string) => {
        if (band === 'High Conviction') return 'text-purple-600 bg-purple-100 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800';
        if (band === 'Strong') return 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800';
        if (band === 'Moderate') return 'text-amber-600 bg-amber-100 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800';
        return 'text-rose-600 bg-rose-100 dark:bg-rose-900/30 border-rose-200 dark:border-rose-800';
    };

    const currentTempScore = Math.max(0, preScore.total + questions.reduce((acc, q) => {
        const ans = answers[q.id];
        if (ans === 'Yes') return acc + 2;
        if (ans === 'No') return acc - 2;
        return acc;
    }, 0));

    const currentBand = logged && finalScoreData ? finalScoreData.band : getBand(currentTempScore);

    const calculateProjectedImpact = (questionId: string, answer: 'Yes' | 'No' | 'Unsure') => {
        const currentAnswer = answers[questionId];
        if (currentAnswer) return 0; // Already answered

        if (answer === 'Yes') return 2;
        if (answer === 'No') return -2;
        return 0;
    };

    return (
        <div className="glass-card p-6 border-t-4 border-t-indigo-500">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-indigo-500" /> Fundamentals
                </h2>
                {logged && (
                    <span className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-500 text-xs font-bold rounded-full flex items-center gap-1">
                        <Lock className="w-3 h-3" /> Locked
                    </span>
                )}
            </div>

            {/* AI Suggestions Toggle */}
            {!logged && suggestions && (
                <div className="mb-6 flex items-center justify-between px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl border border-indigo-100 dark:border-indigo-800">
                    <div className="flex items-center gap-2.5">
                        <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        <span className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">
                            AI-powered suggestions available
                        </span>
                    </div>
                    <button
                        onClick={() => setShowSuggestions(!showSuggestions)}
                        className="text-sm font-bold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-200 transition-colors"
                    >
                        {showSuggestions ? 'Hide' : 'Show'}
                    </button>
                </div>
            )}

            {/* Loading State */}
            {loadingSuggestions && (
                <div className="mb-6 p-8 flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        Generating AI-powered suggestions...
                    </p>
                </div>
            )}

            {/* Error State */}
            {suggestionsError && (
                <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                    <p className="text-sm text-amber-700 dark:text-amber-300">{suggestionsError}</p>
                </div>
            )}

            {/* Questions with Suggestions */}
            <div className="space-y-4 mb-8">
                {questions.map((q, idx) => (
                    <div key={q.id}>
                        {/* Suggestion Tile (if available and enabled) */}
                        {showSuggestions && suggestions && !loadingSuggestions && (
                            <div className="mb-4">
                                <SuggestionTile
                                    question={q.text}
                                    questionId={q.id}
                                    suggestion={
                                        idx === 0 ? suggestions.q1 :
                                            idx === 1 ? suggestions.q2 :
                                                idx === 2 ? suggestions.q3 :
                                                    suggestions.q4
                                    }
                                    onAccept={() => handleAcceptSuggestion(
                                        q.id,
                                        idx === 0 ? suggestions.q1.rec :
                                            idx === 1 ? suggestions.q2.rec :
                                                idx === 2 ? suggestions.q3.rec :
                                                    suggestions.q4.rec
                                    )}
                                    onOverride={(value) => handleAnswer(q.id, value)}
                                    onSkip={() => { }}
                                    userAnswer={answers[q.id]}
                                    disabled={logged}
                                    projectedImpact={calculateProjectedImpact(q.id, 'Yes')}
                                />
                            </div>
                        )}

                        {/* Manual Question Tile (fallback or when suggestions hidden) */}
                        {(!showSuggestions || !suggestions) && (
                            <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700 transition-all hover:border-indigo-200 dark:hover:border-indigo-800">
                                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-3">{q.text}</p>
                                <div className="flex gap-2">
                                    {(['Yes', 'No', 'Unsure'] as const).map((option) => (
                                        <button
                                            key={option}
                                            onClick={() => handleAnswer(q.id, option)}
                                            disabled={logged}
                                            className={clsx(
                                                "flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all",
                                                answers[q.id] === option
                                                    ? option === 'Yes'
                                                        ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/30 scale-105"
                                                        : option === 'No'
                                                            ? "bg-rose-500 text-white shadow-lg shadow-rose-500/30 scale-105"
                                                            : "bg-gray-500 text-white shadow-lg shadow-gray-500/30 scale-105"
                                                    : "bg-white dark:bg-gray-700 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-600"
                                            )}
                                        >
                                            {option} {option === 'Yes' ? `(+${q.points})` : option === 'No' ? `(-${q.points})` : ''}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Summary Card */}
            {showSuggestions && suggestions && !loadingSuggestions && (
                <div className="mb-6">
                    <SummaryCard suggestion={suggestions} />
                </div>
            )}

            {/* Score Display */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-inner mb-6">
                <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-500 font-medium">
                        {logged ? 'Final Score' : 'Estimated Score'}
                    </span>
                    <span className="text-2xl font-black text-gray-900 dark:text-white">
                        {logged ? finalScoreData?.total_score : currentTempScore}
                        <span className="text-lg text-gray-400 font-medium">/20</span>
                    </span>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2.5 mb-4 overflow-hidden">
                    <div
                        className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2.5 rounded-full transition-all duration-1000 ease-out"
                        style={{ width: `${((logged ? finalScoreData?.total_score : currentTempScore) / 20) * 100}%` }}
                    ></div>
                </div>

                <div className={clsx("p-3 rounded-lg border text-center transition-all duration-500", bandColor(currentBand))}>
                    <div className="text-xs uppercase tracking-widest font-bold opacity-70 mb-1">Recommendation</div>
                    <div className="text-lg font-black">{currentBand}</div>
                </div>
            </div>

            {/* Log Decision Button */}
            <button
                onClick={handleLogDecision}
                disabled={logged || !allAnswered || loading}
                className="w-full py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl font-bold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-xl"
            >
                {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : logged ? (
                    <>Decision Logged <CheckCircle2 className="w-4 h-4" /></>
                ) : (
                    <>Log Decision <Save className="w-4 h-4" /></>
                )}
            </button>
        </div>
    );
}
