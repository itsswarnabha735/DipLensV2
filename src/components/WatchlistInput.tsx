'use client';

import { useState } from 'react';
import { searchSymbolAction } from '@/app/actions';
import { useAppStore } from '@/lib/store';
import { Search, Plus, Loader2, CheckCircle2, Upload, List } from 'lucide-react';
import { Instrument } from '@/lib/types';
import clsx from 'clsx';

type ValidationResult = {
    symbol: string;
    status: 'validating' | 'found' | 'not_found' | 'already_added';
    instrument?: Instrument;
};

export default function WatchlistInput() {
    const [mode, setMode] = useState<'search' | 'bulk'>('search');
    const [query, setQuery] = useState('');
    const [bulkInput, setBulkInput] = useState('');
    const [results, setResults] = useState<Instrument[]>([]);
    const [bulkResults, setBulkResults] = useState<ValidationResult[]>([]);
    const [loading, setLoading] = useState(false);

    const addToWatchlist = useAppStore((state) => state.addToWatchlist);
    const activeWatchlistId = useAppStore((state) => state.activeWatchlistId);
    const watchlists = useAppStore((state) => state.watchlists);

    const activeWatchlist = watchlists.find(wl => wl.id === activeWatchlistId);
    const watchlistInstruments = activeWatchlist?.instruments || [];

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        try {
            const data = await searchSymbolAction(query);
            setResults(data);
        } catch (error) {
            console.error('Search failed', error);
        } finally {
            setLoading(false);
        }
    };

    const handleBulkUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!bulkInput.trim() || !activeWatchlistId) return;

        const symbols = bulkInput
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0);

        if (symbols.length === 0) return;

        setLoading(true);
        setBulkResults(symbols.map(symbol => ({ symbol, status: 'validating' })));

        try {
            const validationPromises = symbols.map(async (symbol) => {
                try {
                    const matches = await searchSymbolAction(symbol);
                    if (matches.length > 0) {
                        const instrument = matches[0];
                        const alreadyAdded = watchlistInstruments.some(item => item.symbol === instrument.symbol);
                        return {
                            symbol,
                            status: alreadyAdded ? 'already_added' : 'found',
                            instrument
                        } as ValidationResult;
                    }
                    return { symbol, status: 'not_found' } as ValidationResult;
                } catch {
                    return { symbol, status: 'not_found' } as ValidationResult;
                }
            });

            const results = await Promise.all(validationPromises);
            setBulkResults(results);
        } finally {
            setLoading(false);
        }
    };

    const handleAddAllValid = () => {
        if (!activeWatchlistId) return;

        bulkResults
            .filter(r => r.status === 'found' && r.instrument)
            .forEach(r => r.instrument && addToWatchlist(activeWatchlistId, r.instrument));

        setBulkInput('');
        setBulkResults([]);
    };

    const handleAdd = (e: React.MouseEvent, instrument: Instrument) => {
        e.preventDefault();
        e.stopPropagation();
        if (activeWatchlistId) {
            addToWatchlist(activeWatchlistId, instrument);
        }
        setQuery('');
        setResults([]);
    };

    const isInWatchlist = (symbol: string) => {
        return watchlistInstruments.some(item => item.symbol === symbol);
    };

    const validCount = bulkResults.filter(r => r.status === 'found').length;
    const alreadyAddedCount = bulkResults.filter(r => r.status === 'already_added').length;
    const notFoundCount = bulkResults.filter(r => r.status === 'not_found').length;

    return (
        <div className="w-full max-w-md mx-auto p-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 relative">
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
                Add to {activeWatchlist?.name || 'Watchlist'}
            </h2>

            {/* Mode Toggle */}
            <div className="flex gap-2 mb-4">
                <button
                    onClick={() => {
                        setMode('search');
                        setBulkResults([]);
                        setBulkInput('');
                    }}
                    className={clsx(
                        "flex-1 px-3 py-2 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2",
                        mode === 'search'
                            ? "bg-primary text-white shadow-md"
                            : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                    )}
                >
                    <Search className="w-4 h-4" /> Search
                </button>
                <button
                    onClick={() => {
                        setMode('bulk');
                        setResults([]);
                        setQuery('');
                    }}
                    className={clsx(
                        "flex-1 px-3 py-2 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2",
                        mode === 'bulk'
                            ? "bg-primary text-white shadow-md"
                            : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                    )}
                >
                    <Upload className="w-4 h-4" /> Bulk Upload
                </button>
            </div>

            {/* Search Mode */}
            {mode === 'search' && (
                <>
                    <form onSubmit={handleSearch} className="relative flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search symbol (e.g., RELIANCE.NS)"
                                className="w-full pl-9 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
                        </button>
                    </form>

                    {results.length > 0 && (
                        <div className="mt-4 space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                            {results.map((item) => (
                                <div
                                    key={item.symbol}
                                    className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 border border-transparent hover:border-gray-200 dark:hover:border-gray-600 transition-all group"
                                >
                                    <div>
                                        <div className="font-medium text-gray-900 dark:text-white">{item.symbol}</div>
                                        <div className="text-xs text-gray-500 dark:text-gray-400">{item.name} • {item.exchange}</div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={(e) => handleAdd(e, item)}
                                        disabled={isInWatchlist(item.symbol)}
                                        className={clsx(
                                            "p-2 rounded-full transition-colors",
                                            isInWatchlist(item.symbol)
                                                ? "bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400 cursor-default"
                                                : "text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                                        )}
                                        title={isInWatchlist(item.symbol) ? "Already in Watchlist" : "Add to Watchlist"}
                                    >
                                        {isInWatchlist(item.symbol) ? <CheckCircle2 className="w-5 h-5" /> : <Plus className="w-5 h-5" />}
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}

            {/* Bulk Upload Mode */}
            {mode === 'bulk' && (
                <>
                    <form onSubmit={handleBulkUpload} className="space-y-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Enter comma-separated symbols
                            </label>
                            <textarea
                                value={bulkInput}
                                onChange={(e) => setBulkInput(e.target.value)}
                                placeholder="e.g., RELIANCE.NS, TCS.NS, INFY.NS"
                                rows={4}
                                className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading || !bulkInput.trim()}
                            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><List className="w-4 h-4" /> Validate Symbols</>}
                        </button>
                    </form>

                    {/* Bulk Validation Results */}
                    {bulkResults.length > 0 && (
                        <div className="mt-4 space-y-3">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-gray-600 dark:text-gray-400">
                                    {bulkResults.length} symbol{bulkResults.length !== 1 ? 's' : ''} validated
                                </span>
                                {validCount > 0 && (
                                    <button
                                        onClick={handleAddAllValid}
                                        className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-md font-medium transition-colors"
                                    >
                                        Add {validCount} Valid
                                    </button>
                                )}
                            </div>

                            {/* Summary */}
                            <div className="grid grid-cols-3 gap-2 text-xs">
                                {validCount > 0 && (
                                    <div className="px-2 py-1 bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 rounded text-center font-medium">
                                        ✓ {validCount} Found
                                    </div>
                                )}
                                {alreadyAddedCount > 0 && (
                                    <div className="px-2 py-1 bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded text-center font-medium">
                                        ⊕ {alreadyAddedCount} Added
                                    </div>
                                )}
                                {notFoundCount > 0 && (
                                    <div className="px-2 py-1 bg-rose-100 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300 rounded text-center font-medium">
                                        ✗ {notFoundCount} Not Found
                                    </div>
                                )}
                            </div>

                            {/* Detailed Results */}
                            <div className="max-h-48 overflow-y-auto custom-scrollbar space-y-1">
                                {bulkResults.map((result, idx) => (
                                    <div
                                        key={idx}
                                        className={clsx(
                                            "flex items-center justify-between p-2 rounded-lg text-sm",
                                            result.status === 'validating' && "bg-gray-50 dark:bg-gray-700/30",
                                            result.status === 'found' && "bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800",
                                            result.status === 'already_added' && "bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800",
                                            result.status === 'not_found' && "bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800"
                                        )}
                                    >
                                        <span className={clsx(
                                            "font-mono font-medium",
                                            result.status === 'found' && "text-emerald-700 dark:text-emerald-300",
                                            result.status === 'already_added' && "text-blue-700 dark:text-blue-300",
                                            result.status === 'not_found' && "text-rose-700 dark:text-rose-300",
                                            result.status === 'validating' && "text-gray-500 dark:text-gray-400"
                                        )}>
                                            {result.symbol}
                                        </span>
                                        <span className="text-xs">
                                            {result.status === 'validating' && <Loader2 className="w-3 h-3 animate-spin" />}
                                            {result.status === 'found' && <span className="text-emerald-600 dark:text-emerald-400">✓ Found</span>}
                                            {result.status === 'already_added' && <span className="text-blue-600 dark:text-blue-400">Already Added</span>}
                                            {result.status === 'not_found' && <span className="text-rose-600 dark:text-rose-400">Not Found</span>}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
