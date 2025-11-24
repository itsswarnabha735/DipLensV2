'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { useAlerts, CreateAlertDTO } from '@/hooks/useAlerts';
import { ArrowLeft, Bell, Plus, Trash2, Zap, Activity, Settings2, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

export default function AlertsPage() {
    const watchlists = useAppStore((state) => state.watchlists);
    const { alerts, states, loading, error, createAlert, deleteAlert, fetchLogs } = useAlerts();

    const [newAlert, setNewAlert] = useState<CreateAlertDTO>({
        symbol: '',
        condition: 'dip_gt',
        threshold: 5,
        debounce_seconds: 0,
        priority: 'medium'
    });

    const [expandedAlertId, setExpandedAlertId] = useState<string | null>(null);
    const [logs, setLogs] = useState<any[]>([]);
    const [loadingLogs, setLoadingLogs] = useState(false);

    // Get all instruments from all watchlists
    const allInstruments = watchlists.flatMap(wl => wl.instruments);
    // Deduplicate instruments
    const uniqueInstruments = Array.from(new Set(allInstruments.map(i => i.symbol)))
        .map(symbol => allInstruments.find(i => i.symbol === symbol)!);

    const handleAddAlert = async () => {
        if (!newAlert.symbol || !newAlert.threshold) return;
        try {
            await createAlert(newAlert);
            // Reset form defaults
            setNewAlert({
                symbol: '',
                condition: 'dip_gt',
                threshold: 5,
                debounce_seconds: 0,
                priority: 'medium'
            });
        } catch (e) {
            console.error(e);
        }
    };

    const handleToggleLogs = async (id: string) => {
        if (expandedAlertId === id) {
            setExpandedAlertId(null);
            setLogs([]);
            return;
        }

        setExpandedAlertId(id);
        setLoadingLogs(true);
        try {
            const data = await fetchLogs(id);
            setLogs(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingLogs(false);
        }
    };

    const getStateColor = (state: string) => {
        switch (state?.toLowerCase()) {
            case 'triggered': return 'bg-rose-500 text-white animate-pulse';
            case 'armed': return 'bg-amber-500 text-white';
            case 'cooldown': return 'bg-blue-500 text-white';
            default: return 'bg-gray-100 dark:bg-gray-800 text-gray-500';
        }
    };

    return (
        <div className="min-h-screen p-4 md:p-8 pb-20">
            <div className="max-w-4xl mx-auto space-y-8">
                <div className="flex items-center gap-4">
                    <Link href="/" className="p-3 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-full transition-colors group">
                        <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400 group-hover:-translate-x-1 transition-transform" />
                    </Link>
                    <div>
                        <h1 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight flex items-center gap-3">
                            <Bell className="w-8 h-8 text-primary" /> Alerts Center
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400 font-medium">Monitor dips and technical signals in real-time.</p>
                    </div>
                </div>

                {error && (
                    <div className="bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 p-4 rounded-xl flex items-center gap-3">
                        <AlertTriangle className="w-5 h-5" />
                        {error}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* Create Alert Form */}
                    <div className="md:col-span-1">
                        <div className="glass-card p-6 sticky top-8">
                            <h2 className="text-lg font-bold mb-6 text-gray-900 dark:text-white flex items-center gap-2">
                                <Zap className="w-5 h-5 text-amber-500" /> New Alert
                            </h2>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Symbol</label>
                                    <div className="relative">
                                        <select
                                            className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 focus:ring-2 focus:ring-primary/50 outline-none transition-all appearance-none font-medium"
                                            value={newAlert.symbol}
                                            onChange={e => setNewAlert({ ...newAlert, symbol: e.target.value })}
                                        >
                                            <option value="">Select Ticker</option>
                                            {uniqueInstruments.map(item => (
                                                <option key={item.symbol} value={item.symbol}>{item.symbol}</option>
                                            ))}
                                        </select>
                                        <div className="absolute right-3 top-3.5 pointer-events-none text-gray-400">
                                            <Activity className="w-4 h-4" />
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Condition</label>
                                    <select
                                        className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 focus:ring-2 focus:ring-primary/50 outline-none transition-all appearance-none font-medium"
                                        value={newAlert.condition}
                                        onChange={e => setNewAlert({ ...newAlert, condition: e.target.value })}
                                    >
                                        <option value="dip_gt">Dip &ge; X%</option>
                                        <option value="rsi_lt">RSI &lt; X</option>
                                        <option value="macd_bullish">MACD Bullish</option>
                                        <option value="volume_spike">Volume Spike &gt; X</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Threshold</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 focus:ring-2 focus:ring-primary/50 outline-none transition-all font-bold"
                                        value={newAlert.threshold}
                                        onChange={e => setNewAlert({ ...newAlert, threshold: Number(e.target.value) })}
                                    />
                                </div>

                                {/* Advanced Settings Toggle */}
                                <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
                                    <div className="flex items-center gap-2 mb-2 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                        <Settings2 className="w-3 h-3" /> Sensitivity
                                    </div>
                                    <div className="space-y-3">
                                        <div>
                                            <label className="text-xs text-gray-400 mb-1 block">Debounce (seconds)</label>
                                            <input
                                                type="range"
                                                min="0"
                                                max="300"
                                                step="10"
                                                className="w-full accent-primary"
                                                value={newAlert.debounce_seconds}
                                                onChange={e => setNewAlert({ ...newAlert, debounce_seconds: Number(e.target.value) })}
                                            />
                                            <div className="text-right text-xs font-mono text-gray-500">{newAlert.debounce_seconds}s</div>
                                        </div>
                                    </div>
                                </div>

                                <button
                                    onClick={handleAddAlert}
                                    disabled={!newAlert.symbol || loading}
                                    className="w-full py-3 bg-primary hover:bg-indigo-600 text-white rounded-xl font-bold shadow-lg shadow-indigo-500/30 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
                                >
                                    {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Plus className="w-5 h-5" />}
                                    Create Alert
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Active Alerts List */}
                    <div className="md:col-span-2 space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Active Alerts</h2>
                            <span className="px-3 py-1 bg-gray-100 dark:bg-gray-800 text-gray-500 text-xs font-bold rounded-full">
                                {alerts.length} Monitoring
                            </span>
                        </div>

                        {alerts.length === 0 ? (
                            <div className="text-center py-16 glass-card border-dashed border-2 border-gray-300 dark:border-gray-700">
                                <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Bell className="w-8 h-8 text-gray-400" />
                                </div>
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">No alerts configured</h3>
                                <p className="text-gray-500 text-sm">Set up your first alert to track market moves.</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {alerts.map(alert => {
                                    const state = states[alert.id]?.state || 'idle';
                                    const isExpanded = expandedAlertId === alert.id;

                                    return (
                                        <div key={alert.id} className="glass-card overflow-hidden transition-all">
                                            <div className="p-4 flex items-center justify-between group hover:bg-gray-50/50 dark:hover:bg-gray-800/50 transition-colors">
                                                <div className="flex items-center gap-4 cursor-pointer flex-1" onClick={() => handleToggleLogs(alert.id)}>
                                                    <div className={clsx(
                                                        "w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold transition-colors",
                                                        alert.priority === 'high' ? "bg-rose-100 text-rose-600 dark:bg-rose-900/20 dark:text-rose-400" :
                                                            "bg-primary/10 text-primary"
                                                    )}>
                                                        {alert.symbol.substring(0, 2)}
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-3 mb-1">
                                                            <div className="font-black text-lg text-gray-900 dark:text-white">
                                                                {alert.symbol}
                                                            </div>
                                                            <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide", getStateColor(state))}>
                                                                {state}
                                                            </span>
                                                        </div>
                                                        <div className="text-sm font-medium text-gray-500 flex items-center gap-2">
                                                            <span className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded text-xs font-bold uppercase">
                                                                {alert.condition.replace('_', ' ')}
                                                            </span>
                                                            <span className="font-mono font-bold text-gray-700 dark:text-gray-300">
                                                                {alert.condition.includes('lt') ? '<' : '>='} {alert.threshold}
                                                            </span>
                                                            {alert.debounce_seconds > 0 && (
                                                                <span className="text-xs font-normal text-gray-400 border-l border-gray-200 dark:border-gray-700 pl-2">
                                                                    {alert.debounce_seconds}s delay
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => handleToggleLogs(alert.id)}
                                                        className={clsx(
                                                            "p-2 rounded-lg transition-all",
                                                            isExpanded ? "text-primary bg-primary/10" : "text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                                                        )}
                                                        title="View Logs"
                                                    >
                                                        <Activity className="w-5 h-5" />
                                                    </button>
                                                    <button
                                                        onClick={() => deleteAlert(alert.id)}
                                                        className="p-2 text-gray-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                                        title="Delete Alert"
                                                    >
                                                        <Trash2 className="w-5 h-5" />
                                                    </button>
                                                </div>
                                            </div>

                                            {/* Logs Section */}
                                            {isExpanded && (
                                                <div className="border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/30 p-4">
                                                    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                                                        <Activity className="w-3 h-3" /> Activity Log
                                                    </h4>

                                                    {loadingLogs ? (
                                                        <div className="flex justify-center py-4">
                                                            <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                                                        </div>
                                                    ) : logs.length === 0 ? (
                                                        <div className="text-center py-4 text-sm text-gray-500 italic">
                                                            No activity recorded yet.
                                                        </div>
                                                    ) : (
                                                        <div className="space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                                                            {logs.map((log, i) => (
                                                                <div key={i} className="text-xs flex items-start gap-3 p-2 rounded bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
                                                                    <span className="font-mono text-gray-400 whitespace-nowrap">
                                                                        {new Date(log.timestamp).toLocaleTimeString()}
                                                                    </span>
                                                                    <div>
                                                                        <div className="font-bold text-gray-700 dark:text-gray-300">
                                                                            {log.reason === 'triggered' ? 'Triggered' : `Suppressed: ${log.reason}`}
                                                                        </div>
                                                                        <div className="text-gray-500 mt-0.5">
                                                                            Value: {log.value.toFixed(2)}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
