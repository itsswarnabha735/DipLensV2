'use client';

import { useAppStore } from '@/lib/store';
import { format } from 'date-fns';
import { ArrowLeft, TrendingUp, TrendingDown, Minus, BookOpen, Calendar } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

export default function JournalPage() {
    const journal = useAppStore((state) => state.journal);

    const actionColor = (action: string) => {
        switch (action) {
            case 'Buy': return 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800';
            case 'Skip': return 'text-rose-600 bg-rose-100 dark:bg-rose-900/30 border-rose-200 dark:border-rose-800';
            case 'Wait': return 'text-amber-600 bg-amber-100 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800';
            default: return 'text-gray-600 bg-gray-100 border-gray-200';
        }
    };

    return (
        <div className="min-h-screen p-4 md:p-8 pb-20">
            <div className="max-w-5xl mx-auto space-y-8">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="p-3 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-full transition-colors group">
                            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400 group-hover:-translate-x-1 transition-transform" />
                        </Link>
                        <div>
                            <h1 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight flex items-center gap-3">
                                <BookOpen className="w-8 h-8 text-primary" /> Decision Journal
                            </h1>
                            <p className="text-gray-500 dark:text-gray-400 font-medium">Track your investment decisions and reasoning.</p>
                        </div>
                    </div>
                    <div className="glass px-4 py-2 rounded-full text-sm font-bold text-gray-600 dark:text-gray-300">
                        {journal.length} Entries
                    </div>
                </div>

                {journal.length === 0 ? (
                    <div className="text-center py-24 glass-card border-dashed border-2 border-gray-300 dark:border-gray-700">
                        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                            <BookOpen className="w-8 h-8 text-gray-400" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Your journal is empty</h3>
                        <p className="text-gray-500 mb-6">Log decisions from the stock detail page to see them here.</p>
                        <Link href="/" className="px-6 py-3 bg-primary text-white rounded-xl font-bold hover:bg-indigo-600 transition-colors shadow-lg shadow-indigo-500/30">
                            Explore Stocks
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-6 relative">
                        {/* Timeline Line */}
                        <div className="absolute left-8 top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-700 hidden md:block"></div>

                        {journal.map((entry) => (
                            <div key={entry.id} className="relative md:pl-20">
                                {/* Timeline Dot */}
                                <div className="absolute left-6 top-8 w-4 h-4 rounded-full bg-white dark:bg-gray-900 border-4 border-primary hidden md:block z-10"></div>

                                <div className="glass-card p-6 md:p-8 flex flex-col md:flex-row gap-8 group hover:border-primary/50 transition-colors">
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-3">
                                                <h3 className="text-2xl font-black text-gray-900 dark:text-white">{entry.symbol}</h3>
                                                <span className={clsx("px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 uppercase tracking-wider", actionColor(entry.action))}>
                                                    {entry.action === 'Buy' && <TrendingUp className="w-3 h-3" />}
                                                    {entry.action === 'Skip' && <TrendingDown className="w-3 h-3" />}
                                                    {entry.action === 'Wait' && <Minus className="w-3 h-3" />}
                                                    {entry.action}
                                                </span>
                                            </div>
                                            <span className="text-xs font-bold text-gray-400 flex items-center gap-1 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                                                <Calendar className="w-3 h-3" />
                                                {format(entry.timestamp, 'MMM dd, yyyy HH:mm')}
                                            </span>
                                        </div>

                                        <div className="flex items-center gap-4 mb-6 text-sm">
                                            <div className="flex items-center gap-2">
                                                <span className="text-gray-500">Price:</span>
                                                <span className="font-bold text-gray-900 dark:text-white">{entry.price.toFixed(2)}</span>
                                            </div>
                                            <div className="w-px h-4 bg-gray-300 dark:bg-gray-700"></div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-gray-500">Band:</span>
                                                <span className="font-bold text-gray-900 dark:text-white">{entry.allocationBand}</span>
                                            </div>
                                        </div>

                                        {entry.notes && (
                                            <div className="bg-gray-50/50 dark:bg-gray-800/30 p-4 rounded-xl border border-gray-100 dark:border-gray-700/50 text-sm text-gray-600 dark:text-gray-300 italic relative">
                                                <span className="absolute -top-2 left-4 text-2xl text-gray-300 dark:text-gray-600">"</span>
                                                {entry.notes}
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-8 pt-6 md:pt-0 md:pl-8 md:border-l border-gray-100 dark:border-gray-700/50">
                                        <div className="text-center">
                                            <div className="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-1">Pre-Score</div>
                                            <div className="text-3xl font-black text-gray-900 dark:text-white">{entry.preScore}</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-1">Final</div>
                                            <div className="text-4xl font-black text-primary drop-shadow-sm">{entry.finalScore}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
