import { Instrument, DipSnapshot, IndicatorSnapshot } from './types';

export interface AlertConfig {
    id: string;
    symbol: string;
    condition: 'dip_gt' | 'rsi_lt' | 'macd_bullish';
    threshold: number;
    enabled: boolean;
    lastTriggered?: number;
}

export function checkAlerts(
    alerts: AlertConfig[],
    dips: Record<string, DipSnapshot>,
    indicators: Record<string, IndicatorSnapshot>
): string[] {
    const notifications: string[] = [];

    alerts.forEach(alert => {
        if (!alert.enabled) return;

        const dip = dips[alert.symbol];
        const ind = indicators[alert.symbol];

        if (!dip || !ind) return;

        // Cooldown check (e.g., 1 hour)
        if (alert.lastTriggered && Date.now() - alert.lastTriggered < 3600000) return;

        let triggered = false;
        let message = '';

        switch (alert.condition) {
            case 'dip_gt':
                if (dip.dipPercent >= alert.threshold) {
                    triggered = true;
                    message = `${alert.symbol} Dip is ${dip.dipPercent.toFixed(2)}% (>= ${alert.threshold}%)`;
                }
                break;
            case 'rsi_lt':
                if (ind.rsi < alert.threshold) {
                    triggered = true;
                    message = `${alert.symbol} RSI is ${ind.rsi.toFixed(2)} (< ${alert.threshold})`;
                }
                break;
            case 'macd_bullish':
                if (ind.macd.histogram > 0 && ind.macd.histogram > alert.threshold) {
                    triggered = true;
                    message = `${alert.symbol} MACD Bullish Crossover`;
                }
                break;
        }

        if (triggered) {
            notifications.push(message);
            // In a real app, we'd update lastTriggered here (needs state update)
        }
    });

    return notifications;
}
