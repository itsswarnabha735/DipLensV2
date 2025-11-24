'use client';

import { Instrument, Quote, PreScore, DipClass } from '@/lib/types';
import { ArrowDown, ArrowUp, Activity, TrendingUp, TrendingDown, Trash2 } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';
import { useAppStore } from '@/lib/store';

interface TickerCardProps {
    instrument: Instrument;
    quote?: Quote;
    preScore?: PreScore;
    dipClass?: DipClass;
    dipPercent?: number;
    loading?: boolean;
}

export default function TickerCard({ instrument, quote, preScore, dipClass, dipPercent, loading }: TickerCardProps) {
    const removeFromWatchlist = useAppStore((state) => state.removeFromWatchlist);
    const activeWatchlistId = useAppStore((state) => state.activeWatchlistId);
    const isPositive = quote && quote.change >= 0;

    const handleDelete = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (activeWatchlistId) {
            removeFromWatchlist(activeWatchlistId, instrument.symbol);
        }
    };

    const scoreColor = (score: number) => {
        if (score >= 10) return 'bg-emerald-500 shadow-emerald-500/50';
        if (score >= 6) return 'bg-amber-500 shadow-amber-500/50';
        return 'bg-rose-500 shadow-rose-500/50';
    };

    const dipBadgeStyle = (cls: DipClass) => {
        switch (cls) {
            case 'Major': return 'bg-purple-500/20 text-purple-700 dark:text-purple-300 border-purple-500/30';
            case 'Significant': return 'bg-rose-500/20 text-rose-700 dark:text-rose-300 border-rose-500/30';
            case 'Moderate': return 'bg-orange-500/20 text-orange-700 dark:text-orange-300 border-orange-500/30';
            case 'Minor': return 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/30';
            case 'Micro': return 'bg-blue-500/20 text-blue-700 dark:text-blue-300 border-blue-500/30';
            default: return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20';
        }
    };

    return (
        <div className="glass-card p-5 relative overflow-hidden group">
            {/* Background Gradient Blob */}
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-primary/10 rounded-full blur-3xl group-hover:bg-primary/20 transition-all duration-500"></div>

            <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="font-bold text-xl text-gray-900 dark:text-white tracking-tight">{instrument.symbol}</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 font-medium truncate max-w-[140px]">{instrument.name}</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className={clsx("px-2.5 py-1 rounded-full text-xs font-bold border backdrop-blur-sm", dipBadgeStyle(dipClass || 'None'))}>
                            {dipClass || 'No Dip'}
                        </div>
                        <button
                            onClick={handleDelete}
                            className="p-1.5 text-gray-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-full transition-colors opacity-0 group-hover:opacity-100"
                            title="Remove from Watchlist"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                <div className="flex justify-between items-end mb-5">
                    <div>
                        {loading ? (
                            <div className="h-9 w-28 bg-gray-200 dark:bg-gray-700 animate-pulse rounded-lg"></div>
                        ) : quote ? (
                            <>
                                <div className="text-3xl font-bold text-gray-900 dark:text-white tracking-tighter">
                                    {quote.price.toFixed(2)}
                                </div>
                                <div className={clsx("flex items-center text-sm font-bold mt-1", isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400")}>
                                    {isPositive ? <TrendingUp className="w-4 h-4 mr-1.5" /> : <TrendingDown className="w-4 h-4 mr-1.5" />}
                                    {Math.abs(quote.change).toFixed(2)} ({Math.abs(quote.changePercent).toFixed(2)}%)
                                </div>
                            </>
                        ) : (
                            <span className="text-sm text-gray-400 italic">Data Unavailable</span>
                        )}
                    </div>

                    {preScore && (
                        <div className="text-right">
                            <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Pre-Score</div>
                            <div className="flex items-center justify-end gap-2">
                                <div className={clsx("w-2.5 h-2.5 rounded-full shadow-lg", scoreColor(preScore.total))}></div>
                                <span className="text-2xl font-bold text-gray-900 dark:text-white">{preScore.total}<span className="text-gray-400 text-lg font-normal">/12</span></span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="border-t border-gray-200/50 dark:border-gray-700/50 pt-4 flex justify-between items-center">
                    <div className="text-xs text-gray-400 font-medium">
                        {quote ? (
                            <>
                                {dipPercent && <span className="text-gray-500 dark:text-gray-300 font-bold mr-2">Dip: {dipPercent.toFixed(1)}%</span>}
                                <span className="opacity-60">{new Date(quote.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                            </>
                        ) : '--:--'}
                    </div>
                    <Link
                        href={`/stock/${instrument.symbol}`}
                        className="text-primary hover:text-indigo-500 text-sm font-bold flex items-center transition-colors group/link"
                    >
                        Analyze <Activity className="w-4 h-4 ml-1.5 group-hover/link:translate-x-0.5 transition-transform" />
                    </Link>
                </div>
            </div>
        </div>
    );
}
