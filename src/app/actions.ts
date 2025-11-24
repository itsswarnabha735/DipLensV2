'use server'

import { YahooFinanceService } from '@/lib/yahoo-service';
import { Quote, Instrument } from '@/lib/types';

export async function getQuoteAction(symbol: string): Promise<Quote | null> {
    return await YahooFinanceService.getQuote(symbol);
}

export async function getHistoricalDataAction(symbol: string, periodDays: number = 365) {
    return await YahooFinanceService.getHistoricalData(symbol, periodDays);
}

export async function searchSymbolAction(query: string): Promise<Instrument[]> {
    return await YahooFinanceService.searchSymbol(query);
}
