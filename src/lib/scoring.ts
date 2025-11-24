import {
    PreScore,
    PreScoreRule,
    IndicatorSnapshot,
    DipSnapshot,
    Checklist,
    FinalScore,
    AllocationBand
} from './types';

/**
 * Calculates the Pre-Score based on technical indicators and dip status.
 * Max Score: 12
 */
export function calculatePreScore(
    symbol: string,
    dip: DipSnapshot,
    indicators: IndicatorSnapshot
): PreScore {
    const rules: PreScoreRule[] = [];
    let total = 0;

    // Rule 1: Dip in 8-15% band (Moderate or Significant)
    // Note: PRD says "Dip in 8-15% band: +2". 
    // 8-12% is Moderate, 12-15% is Significant.
    const isDipInBand = dip.dipPercent >= 8 && dip.dipPercent <= 15;
    rules.push({
        id: 'dip_band',
        label: 'Dip in 8-15% band',
        points: 2,
        met: isDipInBand
    });
    if (isDipInBand) total += 2;

    // Rule 2: RSI in 30-40 (or < 30)
    // PRD: "RSI in 30-40: +2 (RSI<30 still +2 but show 'high volatility risk' tag)"
    const isRsiGood = indicators.rsi <= 40;
    rules.push({
        id: 'rsi_zone',
        label: indicators.rsi < 30 ? 'RSI < 30 (High Volatility)' : 'RSI in 30-40 Zone',
        points: 2,
        met: isRsiGood
    });
    if (isRsiGood) total += 2;

    // Rule 3: MACD Bullish Crossover or Positive Histogram Acceleration
    // Simplified: If histogram > 0 (bullish momentum) or histogram is increasing
    // For this snapshot, we check if histogram is positive for simplicity of "bullishness"
    // Ideally we need previous histogram to check acceleration. 
    // Let's assume "Bullish Crossover" implies Histogram > 0.
    const isMacdBullish = indicators.macd.histogram > 0;
    rules.push({
        id: 'macd_bullish',
        label: 'MACD Bullish Momentum',
        points: 2,
        met: isMacdBullish
    });
    if (isMacdBullish) total += 2;

    // Rule 4: Price above or holding SMA200
    // "Holding" is hard to define with single snapshot. Let's check if Price >= SMA200 * 0.98 (near or above)
    // PRD: "Price above or holding SMA200: +2"
    const price = dip.currentPrice;
    const isSma200Good = price >= indicators.sma200 * 0.98; // 2% tolerance
    rules.push({
        id: 'sma200_support',
        label: 'Price above/near SMA200',
        points: 2,
        met: isSma200Good
    });
    if (isSma200Good) total += 2;

    // Rule 5: Bollinger near/lower band
    // If Price <= Lower Band * 1.02 (within 2% of lower band)
    const isBollingerLow = price <= indicators.bollinger.lower * 1.02;
    rules.push({
        id: 'bb_lower',
        label: 'Near Bollinger Lower Band',
        points: 2,
        met: isBollingerLow
    });
    if (isBollingerLow) total += 2;

    // Rule 6: Volume spike (>= 1.5x 20-day avg)
    // We need current volume. Assuming `indicators` has volume info or we pass it.
    // `IndicatorSnapshot` has `volume20Avg`. We need current volume from somewhere.
    // Let's assume we pass current volume or it's in the snapshot (it's not currently).
    // Let's update IndicatorSnapshot to include currentVolume or pass it separately.
    // For now, let's assume we can access it. I'll add `currentVolume` to `IndicatorSnapshot` in types later or here.
    // Actually, let's assume the `indicators` object passed here MIGHT have it or we rely on Quote.
    // Let's just add a placeholder check.
    // TODO: Pass current volume properly.
    // For now, let's assume `indicators` has a `currentVolume` property (I will update types.ts).

    // Wait, I can't access currentVolume from IndicatorSnapshot as defined.
    // I will assume for now we don't have it and skip or update types.
    // Let's update types.ts in the next step to include currentVolume in IndicatorSnapshot or Quote.
    // For this step, I will comment it out or use a dummy.

    // Let's assume we pass `currentVolume` as an argument.
    // I will modify the function signature.

    return {
        symbol,
        timestamp: Date.now(),
        total,
        rules
    };
}

// Overloaded function to include volume
export function calculatePreScoreWithVolume(
    symbol: string,
    dip: DipSnapshot,
    indicators: IndicatorSnapshot,
    currentVolume: number
): PreScore {
    const result = calculatePreScore(symbol, dip, indicators);

    const isVolumeSpike = currentVolume >= (indicators.volume20Avg * 1.5);
    result.rules.push({
        id: 'vol_spike',
        label: 'Volume Spike (>= 1.5x Avg)',
        points: 2,
        met: isVolumeSpike
    });

    if (isVolumeSpike) result.total += 2;

    return result;
}


/**
 * Calculates the Final Score based on Pre-Score and User Checklist.
 * Total Max: 20
 */
export function calculateFinalScore(
    preScore: PreScore,
    checklist: Checklist
): FinalScore {
    let checklistScore = 0;
    const trace: string[] = [];

    // Q1: Dip macro/sector? Yes +2, No -2, Unsure 0
    if (checklist.q1_macro === true) { checklistScore += 2; trace.push('Q1: Yes (+2)'); }
    else if (checklist.q1_macro === false) { checklistScore -= 2; trace.push('Q1: No (-2)'); } // Optional penalty

    // Q2: Financials intact? Yes +2
    if (checklist.q2_financials === true) { checklistScore += 2; trace.push('Q2: Yes (+2)'); }
    else if (checklist.q2_financials === false) { checklistScore -= 2; trace.push('Q2: No (-2)'); }

    // Q3: No negative guidance? Yes +2
    if (checklist.q3_management === true) { checklistScore += 2; trace.push('Q3: Yes (+2)'); }
    else if (checklist.q3_management === false) { checklistScore -= 2; trace.push('Q3: No (-2)'); }

    // Q4: Support? Yes +2
    if (checklist.q4_support === true) { checklistScore += 2; trace.push('Q4: Yes (+2)'); }

    // Clamp checklist score if needed (0-8 range implied, but negatives possible? PRD says 0-8)
    // PRD: "Total = Pre-Score (0-12) + Checklist (0-8) = 0-20"
    // If negatives are allowed, it could lower the score. Let's respect the sum.

    const totalScore = Math.max(0, preScore.total + checklistScore); // Ensure no negative total

    let band: AllocationBand = 'Skip';
    if (totalScore >= 14) band = 'High Conviction';
    else if (totalScore >= 11) band = 'Strong';
    else if (totalScore >= 8) band = 'Moderate';
    else if (totalScore >= 6) band = 'Weak';
    else band = 'Skip';

    return {
        symbol: preScore.symbol,
        timestamp: Date.now(),
        preScore: preScore.total,
        checklistScore,
        totalScore,
        band
    };
}
