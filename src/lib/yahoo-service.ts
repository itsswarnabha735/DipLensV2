import YahooFinance from 'yahoo-finance2';
import { Quote, Instrument } from './types';

const yahooFinance = new YahooFinance();

export interface HistoricalDataPoint {
    date: Date;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    adjClose?: number;
}

export class YahooFinanceService {
    /**
     * Fetches the current quote for a symbol.
     */
    static async getQuote(symbol: string): Promise<Quote | null> {
        try {
            const result = await yahooFinance.quote(symbol) as any;
            if (!result) return null;

            return {
                symbol: result.symbol,
                price: result.regularMarketPrice || 0,
                change: result.regularMarketChange || 0,
                changePercent: result.regularMarketChangePercent || 0,
                volume: result.regularMarketVolume || 0,
                timestamp: result.regularMarketTime ? result.regularMarketTime.getTime() : Date.now(),
            };
        } catch (error) {
            console.error(`Error fetching quote for ${symbol}:`, error);
            return null;
        }
    }

    /**
     * Fetches historical data for a symbol.
     * Defaults to 1 year of daily data for 52-week high and indicators.
     */
    static async getHistoricalData(symbol: string, periodDays: number = 365): Promise<HistoricalDataPoint[]> {
        try {
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - periodDays);

            const result = await yahooFinance.historical(symbol, {
                period1: startDate,
                period2: endDate,
                interval: '1d',
            }) as any[];

            return result.map((row: any) => ({
                date: row.date,
                open: row.open,
                high: row.high,
                low: row.low,
                close: row.close,
                volume: row.volume,
                adjClose: row.adjClose,
            }));
        } catch (error) {
            console.error(`Error fetching history for ${symbol}:`, error);
            return [];
        }
    }

    /**
     * Validates a symbol and returns instrument details if valid.
     */
    static async searchSymbol(query: string): Promise<Instrument[]> {
        try {
            const result = await yahooFinance.search(query) as any;
            return result.quotes
                .filter((q: any) => q.isYahooFinance) // Filter for valid quotes
                .map((q: any) => ({
                    id: q.symbol,
                    symbol: q.symbol,
                    exchange: q.exchange,
                    name: q.shortname || q.longname || q.symbol,
                    sector: q.sector,
                    lastPrice: 0 // Placeholder
                }));
        } catch (error) {
            console.error(`Error searching symbol ${query}:`, error);
            return [];
        }
    }
}
