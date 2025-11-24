// import { MarketData, Stock } from './types';

const API_BASE_URL = 'http://127.0.0.1:8000';

export interface SectorSnapshot {
    sector_id: string;
    sector_name: string;
    ts: string;
    dip_pct: number;
    rsi40_breadth: number;
    sma200_up_breadth: number;
    lowerband_breadth: number;
    constituents_count: number;
    avg_volume_ratio: number;
}

export interface Candidate {
    symbol: string;
    rank: number;
    pre_score: number;
    reasons: string[];
    flags: string[];
    distance_to_sma200_pct: number;
    distance_to_lower_band_pct: number;
    adtv: number;
}

export interface SuggestionBundle {
    bundle_id: string;
    event_id: string;
    sector_id: string;
    ts: string;
    candidates: Candidate[];
    severity_tags: string[];
}

export interface DipAnalysis {
    symbol: string;
    current_price: number;
    high_52w: number;
    high_52w_date: string | null;
    dip_pct: number;
    dip_class: string;
    days_from_high: number | null;
}

export interface Indicators {
    rsi: number | null;
    macd: {
        macd: number;
        signal: number;
        histogram: number;
    } | null;
    sma50: number | null;
    sma200: number | null;
    bollinger: {
        upper: number;
        middle: number;
        lower: number;
    } | null;
    volume_avg: number | null;
}

export const api = {
    async getSectorSnapshots(): Promise<SectorSnapshot[]> {
        const res = await fetch(`${API_BASE_URL}/sectors/snapshots`);
        if (!res.ok) throw new Error('Failed to fetch sector snapshots');
        return res.json();
    },

    async getSectorCandidates(sectorId: string): Promise<Candidate[]> {
        const res = await fetch(`${API_BASE_URL}/sectors/${sectorId}/candidates`);
        if (!res.ok) throw new Error('Failed to fetch sector candidates');
        return res.json();
    },

    async getSectorEvent(sectorId: string): Promise<SuggestionBundle | null> {
        const res = await fetch(`${API_BASE_URL}/sectors/${sectorId}/event`);
        if (!res.ok) throw new Error('Failed to fetch sector event');
        return res.json();
    },

    async getDipAnalysis(symbol: string): Promise<DipAnalysis> {
        const res = await fetch(`${API_BASE_URL}/dips/${symbol}`);
        if (!res.ok) throw new Error('Failed to fetch dip analysis');
        return res.json();
    },

    async getIndicators(symbol: string): Promise<Indicators> {
        const res = await fetch(`${API_BASE_URL}/indicators/${symbol}`);
        if (!res.ok) throw new Error('Failed to fetch indicators');
        return res.json();
    },

    async getBars(symbol: string, interval: string = '1d', lookback: string = '1y'): Promise<any> {
        const res = await fetch(`${API_BASE_URL}/bars?symbol=${symbol}&interval=${interval}&lookback=${lookback}`);
        if (!res.ok) throw new Error('Failed to fetch bars');
        return res.json();
    },

    async getFullAnalysis(symbol: string, lookback: string = '1y'): Promise<{
        symbol: string;
        bars: any[];
        dip_analysis: DipAnalysis;
        indicators: Indicators;
    }> {
        const res = await fetch(`${API_BASE_URL}/stock/${symbol}/full-analysis?lookback=${lookback}`);
        if (!res.ok) throw new Error('Failed to fetch full analysis');
        return res.json();
    },

    async submitChecklist(symbol: string, checklist: any): Promise<any> {
        const res = await fetch(`${API_BASE_URL}/scores/${symbol}/checklist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(checklist)
        });
        if (!res.ok) throw new Error('Failed to submit checklist');
        return res.json();
    },

    async getLatestInsight(symbol: string): Promise<any> {
        const res = await fetch(`${API_BASE_URL}/insights/${symbol}/latest`, { cache: 'no-store' });
        if (!res.ok) throw new Error('Failed to fetch insights');
        return res.json();
    },

    async getFundamentalsSuggestions(symbol: string): Promise<any> {
        const res = await fetch(`${API_BASE_URL}/fundamentals/${symbol}/suggestions`, { cache: 'no-store' });
        if (!res.ok) throw new Error('Failed to fetch fundamentals suggestions');
        return res.json();
    }
};
