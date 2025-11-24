"use client";

import React, { useEffect, useState } from 'react';
import { api, Candidate, SuggestionBundle, SectorSnapshot } from '@/lib/api';
import { ArrowLeft, AlertTriangle, CheckCircle, TrendingUp, AlertOctagon } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function SectorDetailPage() {
    const params = useParams();
    const sectorId = params.id as string;

    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [event, setEvent] = useState<SuggestionBundle | null>(null);
    const [snapshot, setSnapshot] = useState<SectorSnapshot | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                // Parallel fetch
                const [candidatesData, eventData, snapshotsData] = await Promise.all([
                    api.getSectorCandidates(sectorId),
                    api.getSectorEvent(sectorId),
                    api.getSectorSnapshots() // Inefficient but simple for now to get single snapshot
                ]);

                setCandidates(candidatesData);
                setEvent(eventData);

                const currentSector = snapshotsData.find(s => s.sector_id === sectorId);
                if (currentSector) setSnapshot(currentSector);

            } catch (error) {
                console.error("Failed to fetch sector details", error);
            } finally {
                setLoading(false);
            }
        };

        if (sectorId) {
            fetchData();
        }
    }, [sectorId]);

    const getScoreColor = (score: number) => {
        if (score >= 10) return 'bg-green-500/20 text-green-400 border-green-500/30';
        if (score >= 7) return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
        if (score >= 4) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    };

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-gray-100 p-6 pb-24">
            <div className="mb-6">
                <Link href="/sectors-radar" className="flex items-center text-gray-400 hover:text-white transition-colors mb-4">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Radar
                </Link>

                <div className="flex justify-between items-end">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2">
                            {snapshot?.sector_name || sectorId}
                        </h1>
                        <div className="flex gap-4 text-sm text-gray-400">
                            <span>Dip: <span className="text-white font-mono">-{snapshot?.dip_pct}%</span></span>
                            <span>RSI&lt;40: <span className="text-white font-mono">{(snapshot?.rsi40_breadth || 0) * 100}%</span></span>
                        </div>
                    </div>

                    {event && (
                        <div className="px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
                            <AlertOctagon className="w-5 h-5 text-red-400 animate-pulse" />
                            <div>
                                <div className="text-red-400 font-semibold text-sm">Active Alert</div>
                                <div className="text-red-300/70 text-xs">Sector in buy zone</div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {loading ? (
                <div className="flex justify-center items-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                </div>
            ) : (
                <div className="space-y-8">
                    {/* Candidates List */}
                    <div>
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-blue-400" />
                            Top Candidates
                        </h2>

                        <div className="grid gap-4">
                            {candidates.map((candidate) => (
                                <div key={candidate.symbol} className="glass-card p-4 rounded-xl border border-white/5 hover:border-white/10 transition-all">
                                    <div className="flex justify-between items-start">
                                        <div className="flex items-start gap-4">
                                            <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-lg font-bold border ${getScoreColor(candidate.pre_score)}`}>
                                                {candidate.pre_score}
                                            </div>
                                            <div>
                                                <Link href={`/stock/${candidate.symbol}`} className="text-lg font-bold hover:text-blue-400 transition-colors">
                                                    {candidate.symbol}
                                                </Link>
                                                <div className="flex flex-wrap gap-2 mt-2">
                                                    {candidate.reasons.map((reason, i) => (
                                                        <span key={i} className="px-2 py-0.5 rounded text-xs bg-white/5 text-gray-300 border border-white/10">
                                                            {reason}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="text-right space-y-1">
                                            {candidate.flags.includes('volatility_risk') && (
                                                <div className="flex items-center justify-end gap-1 text-orange-400 text-xs">
                                                    <AlertTriangle className="w-3 h-3" />
                                                    <span>High Volatility</span>
                                                </div>
                                            )}
                                            <div className="text-xs text-gray-500">
                                                ADTV: {(candidate.adtv / 10000000).toFixed(1)}Cr
                                            </div>
                                        </div>
                                    </div>

                                    <div className="mt-4 pt-3 border-t border-white/5 grid grid-cols-2 gap-4 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-gray-500">vs SMA200</span>
                                            <span className={candidate.distance_to_sma200_pct > 0 ? 'text-green-400' : 'text-red-400'}>
                                                {candidate.distance_to_sma200_pct > 0 ? '+' : ''}{candidate.distance_to_sma200_pct.toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-500">vs Lower Band</span>
                                            <span className={candidate.distance_to_lower_band_pct > 0 ? 'text-green-400' : 'text-red-400'}>
                                                {candidate.distance_to_lower_band_pct > 0 ? '+' : ''}{candidate.distance_to_lower_band_pct.toFixed(1)}%
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {candidates.length === 0 && (
                                <div className="text-center py-12 text-gray-500 bg-white/5 rounded-xl">
                                    No candidates meet the criteria currently.
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
