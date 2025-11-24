import { DipClass } from './types';

/**
 * Calculates Simple Moving Average (SMA)
 */
export function calculateSMA(data: number[], period: number): number {
    if (data.length < period) return 0;
    const slice = data.slice(-period);
    const sum = slice.reduce((a, b) => a + b, 0);
    return sum / period;
}

/**
 * Calculates Relative Strength Index (RSI)
 * Standard period: 14
 */
export function calculateRSI(prices: number[], period: number = 14): number {
    if (prices.length < period + 1) return 0;

    let gains = 0;
    let losses = 0;

    // Calculate initial average gain/loss
    for (let i = 1; i <= period; i++) {
        const change = prices[i] - prices[i - 1];
        if (change > 0) gains += change;
        else losses += Math.abs(change);
    }

    let avgGain = gains / period;
    let avgLoss = losses / period;

    // Smooth subsequent values
    for (let i = period + 1; i < prices.length; i++) {
        const change = prices[i] - prices[i - 1];
        const gain = change > 0 ? change : 0;
        const loss = change < 0 ? Math.abs(change) : 0;

        avgGain = (avgGain * (period - 1) + gain) / period;
        avgLoss = (avgLoss * (period - 1) + loss) / period;
    }

    if (avgLoss === 0) return 100;
    const rs = avgGain / avgLoss;
    return 100 - (100 / (1 + rs));
}

/**
 * Calculates MACD (Moving Average Convergence Divergence)
 * Standard: 12, 26, 9
 */
export function calculateMACD(prices: number[], fastPeriod: number = 12, slowPeriod: number = 26, signalPeriod: number = 9) {
    if (prices.length < slowPeriod + signalPeriod) {
        return { macd: 0, signal: 0, histogram: 0 };
    }

    const ema = (data: number[], period: number) => {
        const k = 2 / (period + 1);
        let ema = data[0];
        const result = [ema];
        for (let i = 1; i < data.length; i++) {
            ema = (data[i] * k) + (ema * (1 - k));
            result.push(ema);
        }
        return result;
    };

    const fastEMA = ema(prices, fastPeriod);
    const slowEMA = ema(prices, slowPeriod);

    // MACD Line = Fast EMA - Slow EMA
    // We need to align the arrays since slowEMA starts later effectively (or rather, stabilizes later)
    // But for simplicity in this array-based approach, we just subtract index by index.
    // However, standard calculation usually implies we have enough data.

    const macdLine: number[] = [];
    for (let i = 0; i < prices.length; i++) {
        macdLine.push(fastEMA[i] - slowEMA[i]);
    }

    const signalLine = ema(macdLine, signalPeriod);

    const currentMACD = macdLine[macdLine.length - 1];
    const currentSignal = signalLine[signalLine.length - 1];
    const histogram = currentMACD - currentSignal;

    return {
        macd: currentMACD,
        signal: currentSignal,
        histogram
    };
}

/**
 * Calculates Bollinger Bands
 * Standard: 20, 2
 */
export function calculateBollingerBands(prices: number[], period: number = 20, stdDevMultiplier: number = 2) {
    if (prices.length < period) {
        return { upper: 0, middle: 0, lower: 0 };
    }

    const sma = calculateSMA(prices, period);
    const slice = prices.slice(-period);

    const squaredDiffs = slice.map(p => Math.pow(p - sma, 2));
    const avgSquaredDiff = squaredDiffs.reduce((a, b) => a + b, 0) / period;
    const stdDev = Math.sqrt(avgSquaredDiff);

    return {
        upper: sma + (stdDev * stdDevMultiplier),
        middle: sma,
        lower: sma - (stdDev * stdDevMultiplier)
    };
}

/**
 * Calculates Dip Percentage and Class
 */
export function calculateDip(currentPrice: number, high52Week: number): { dipPercent: number, dipClass: DipClass } {
    if (high52Week <= 0) return { dipPercent: 0, dipClass: 'None' };

    const dipRaw = (high52Week - currentPrice) / high52Week * 100;
    const dipPercent = Math.max(0, dipRaw);

    let dipClass: DipClass = 'None';
    if (dipPercent >= 15) dipClass = 'Major';
    else if (dipPercent >= 12) dipClass = 'Significant';
    else if (dipPercent >= 8) dipClass = 'Moderate';
    else if (dipPercent >= 5) dipClass = 'Minor';
    else if (dipPercent >= 3) dipClass = 'Micro';

    return { dipPercent, dipClass };
}
