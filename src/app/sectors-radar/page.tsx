"use client";

import React, { useEffect, useState } from 'react';
import { api, SectorSnapshot } from '@/lib/api';
import { ArrowDown, ArrowUp, Activity, Layers, Clock, RefreshCw, Settings } from 'lucide-react';
import Link from 'next/link';

export default function SectorRadarPage() {
    const [snapshots, setSnapshots] = useState<SectorSnapshot[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    const fetchSnapshots = async () => {
        try {
            const data = await api.getSectorSnapshots();
            setSnapshots(data);
            setLastUpdated(new Date());
        } catch (error) {
            console.error("Failed to fetch sector snapshots", error);
        } finally {
            setLoading(false);
        }
    };

    const triggerRefresh = async () => {
        setRefreshing(true);
        try {
            const response = await fetch('http://localhost:8000/sectors/refresh-cache', {
                method: 'POST',
            });
            const data = await response.json();
            console.log('Cache refresh started:', data);

            // Poll for updates after estimated time
            setTimeout(() => {
                fetchSnapshots();
                setRefreshing(false);
            }, data.estimated_time_seconds * 1000 || 240000);
        } catch (error) {
            console.error("Failed to trigger cache refresh", error);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchSnapshots();
        const interval = setInterval(fetchSnapshots, 15000); // Poll every 15s
        return () => clearInterval(interval);
    }, []);

    const getBreadthColor = (value: number) => {
        if (value > 0.7) return 'text-green-400';
        if (value > 0.4) return 'text-yellow-400';
        return 'text-red-400';
    };

    const getDipColor = (dip: number) => {
        if (dip > 15) return 'text-red-500 font-bold';
        if (dip > 10) return 'text-orange-400 font-bold';
        if (dip > 5) return 'text-yellow-400';
        return 'text-gray-400';
    };

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-gray-100 p-6 pb-24">
            <header className="mb-8 flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                        Sector Radar
                    </h1>
                    <p className="text-gray-400 mt-1">Real-time sector breadth & dip monitoring</p>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                        <Clock className="w-4 h-4" />
                        <span>Updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : '--:--'}</span>
                    </div>

                    {/* Manual Refresh Button */}
                    <button
                        onClick={triggerRefresh}
                        disabled={refreshing}
                        className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 backdrop-blur-md border border-white/10 rounded-full transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
                        title="Manually refresh sector data (takes ~3-4 minutes)"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
                        <span className="text-sm font-medium">
                            {refreshing ? 'Refreshing...' : 'Refresh Data'}
                        </span>
                    </button>
                </div>
            </header>

            {refreshing && (
                <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center gap-3">
                    <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />
                    <div>
                        <p className="text-blue-400 font-medium">Fetching fresh sector data from NSE...</p>
                        <p className="text-gray-400 text-sm">This will take approximately 3-4 minutes. You can continue using other features.</p>
                    </div>
                </div>
            )}

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Skeleton loaders */}
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                        <div key={i} className="glass-card p-5 rounded-xl border border-white/10 animate-pulse">
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex-1">
                                    <div className="h-6 bg-gray-700 rounded w-3/4 mb-2"></div>
                                    <div className="h-4 bg-gray-800 rounded w-1/2"></div>
                                </div>
                                <div className="w-16 h-16 bg-gray-700 rounded-xl"></div>
                            </div>
                            <div className="space-y-4">
                                <div className="h-2 bg-gray-800 rounded-full"></div>
                                <div className="h-2 bg-gray-800 rounded-full"></div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : snapshots.length === 0 ? (
                <div className="text-center py-24 glass-card border-dashed border-2 border-white/10">
                    <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Layers className="w-8 h-8 text-gray-500" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">No sector data available</h3>
                    <p className="text-gray-400 mb-6">Unable to load sector information. Please try again.</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-600/30"
                    >
                        Reload Page
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {snapshots.map((sector) => (
                        <Link href={`/sectors/${sector.sector_id}`} key={sector.sector_id}>
                            <div className="glass-card p-5 rounded-xl hover:bg-white/5 transition-all cursor-pointer border border-white/10 hover:border-blue-500/30 group">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-xl font-semibold text-gray-100 group-hover:text-blue-400 transition-colors">
                                            {sector.sector_name}
                                        </h3>
                                        <span className="text-xs text-gray-500">{sector.constituents_count} Constituents</span>
                                    </div>
                                    <div className="text-right">
                                        <div className={`text-2xl ${getDipColor(sector.dip_pct)}`}>
                                            -{sector.dip_pct}%
                                        </div>
                                        <div className="text-xs text-gray-500">Avg Dip</div>
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    {/* Breadth Meters */}
                                    <div>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-gray-400">RSI &lt; 40</span>
                                            <span className={getBreadthColor(1 - sector.rsi40_breadth)}>
                                                {(sector.rsi40_breadth * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-blue-600 to-blue-400"
                                                style={{ width: `${sector.rsi40_breadth * 100}%` }}
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-gray-400">Above SMA200</span>
                                            <span className={getBreadthColor(sector.sma200_up_breadth)}>
                                                {(sector.sma200_up_breadth * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-green-600 to-green-400"
                                                style={{ width: `${sector.sma200_up_breadth * 100}%` }}
                                            />
                                        </div>
                                    </div>

                                    <div className="pt-3 border-t border-white/5 flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <Activity className="w-4 h-4 text-purple-400" />
                                            <span className="text-sm text-gray-300">Vol Ratio: <span className="font-mono">{sector.avg_volume_ratio}x</span></span>
                                        </div>
                                        {sector.lowerband_breadth > 0.3 && (
                                            <span className="px-2 py-1 rounded bg-red-500/20 text-red-300 text-xs border border-red-500/30">
                                                Oversold
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
