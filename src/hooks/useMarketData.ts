import { useEffect, useRef } from 'react';
import { useAppStore } from '@/lib/store';
import { getQuoteAction, getHistoricalDataAction } from '@/app/actions';
import { calculateSMA, calculateRSI, calculateMACD, calculateBollingerBands, calculateDip } from '@/lib/indicators';
import { calculatePreScore } from '@/lib/scoring';
import { IndicatorSnapshot, DipSnapshot, Instrument } from '@/lib/types';

export function useMarketData() {
    const watchlists = useAppStore((state) => state.watchlists);
    const activeWatchlistId = useAppStore((state) => state.activeWatchlistId);
    const updateQuote = useAppStore((state) => state.updateQuote);
    const updateDip = useAppStore((state) => state.updateDip);
    const updatePreScore = useAppStore((state) => state.updatePreScore);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    // Get instruments from active watchlist
    const activeWatchlist = watchlists.find(wl => wl.id === activeWatchlistId);
    const instruments = activeWatchlist?.instruments || [];

    const fetchData = async () => {
        if (instruments.length === 0) return;

        console.log('Fetching market data for watchlist...', instruments.map(i => i.symbol));

        for (const item of instruments) {
            try {
                // Parallel fetch for speed
                const [quote, history] = await Promise.all([
                    getQuoteAction(item.symbol),
                    getHistoricalDataAction(item.symbol, 365)
                ]);

                if (quote) {
                    updateQuote(quote);

                    if (history.length > 50) { // Need enough data for indicators
                        const closes = history.map(h => h.close);
                        const highs = history.map(h => h.high);

                        // Calculate Indicators
                        const rsi = calculateRSI(closes);
                        const sma50 = calculateSMA(closes, 50);
                        const sma200 = calculateSMA(closes, 200);
                        const macd = calculateMACD(closes);
                        const bollinger = calculateBollingerBands(closes);
                        const vol20 = calculateSMA(history.map(h => h.volume), 20);

                        const indicators: IndicatorSnapshot = {
                            symbol: item.symbol,
                            timestamp: Date.now(),
                            rsi,
                            sma50,
                            sma200,
                            macd,
                            bollinger,
                            volume20Avg: vol20
                        };

                        // Calculate Dip
                        const high52 = Math.max(...highs); // Simple 52w high from history
                        const dip = calculateDip(quote.price, high52);

                        const dipSnapshot: DipSnapshot = {
                            symbol: item.symbol,
                            timestamp: Date.now(),
                            currentPrice: quote.price,
                            high52Week: high52,
                            dipPercent: dip.dipPercent,
                            dipClass: dip.dipClass
                        };

                        updateDip(dipSnapshot);

                        // Calculate Pre-Score
                        const preScore = calculatePreScore(item.symbol, dipSnapshot, indicators);
                        updatePreScore(preScore);
                    }
                }
            } catch (error) {
                console.error(`Error updating data for ${item.symbol}:`, error);
            }
        }
    };

    useEffect(() => {
        fetchData(); // Initial fetch

        // Poll every 60 seconds to respect rate limits and avoid spamming
        pollingRef.current = setInterval(fetchData, 60000);

        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, [instruments.length]); // Re-run if watchlist changes (simple trigger)

    return { refresh: fetchData };
}
