import { useState, useEffect, useCallback } from 'react';

export interface AlertRule {
    id: string;
    user_id: string;
    symbol: string;
    condition: 'dip_gt' | 'rsi_lt' | 'macd_bullish' | 'volume_spike' | 'pre_score_gt';
    threshold: number;
    debounce_seconds: number;
    hysteresis_reset: number;
    confirm_window_seconds: number;
    enabled: boolean;
    cooldown_seconds: number;
    priority: 'high' | 'medium' | 'low';
    created_at: string;
    updated_at: string;
}

export interface CreateAlertDTO {
    symbol: string;
    condition: string;
    threshold: number;
    debounce_seconds?: number;
    priority?: string;
}

const API_BASE = 'http://localhost:8000/alerts';

export function useAlerts() {
    const [alerts, setAlerts] = useState<AlertRule[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [states, setStates] = useState<Record<string, any>>({});

    const fetchAlerts = useCallback(async () => {
        try {
            setLoading(true);
            const [rulesRes, statesRes] = await Promise.all([
                fetch(API_BASE + '/'),
                fetch(API_BASE + '/states')
            ]);

            if (!rulesRes.ok) throw new Error('Failed to fetch alerts');

            const rulesData = await rulesRes.json();
            setAlerts(rulesData);

            if (statesRes.ok) {
                const statesData = await statesRes.json();
                // Convert array to map for easier lookup
                const statesMap = statesData.reduce((acc: any, curr: any) => {
                    acc[curr.rule_id] = curr;
                    return acc;
                }, {});
                setStates(statesMap);
            }

            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, []);

    const createAlert = async (dto: CreateAlertDTO) => {
        try {
            // Generate a unique ID for the alert
            const id = `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            const now = new Date().toISOString();

            const payload = {
                id,
                user_id: 'default_user',
                symbol: dto.symbol,
                condition: dto.condition,
                threshold: dto.threshold,
                debounce_seconds: dto.debounce_seconds || 0,
                hysteresis_reset: 0,
                confirm_window_seconds: 0,
                enabled: true,
                cooldown_seconds: 3600,
                priority: dto.priority || 'medium',
                created_at: now,
                updated_at: now
            };

            const res = await fetch(API_BASE + '/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`Failed to create alert: ${errorText}`);
            }

            const newAlert = await res.json();
            setAlerts(prev => [...prev, newAlert]);
            // Refresh states to include new alert
            fetchAlerts();
            return newAlert;
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to create alert';
            setError(errorMsg);
            console.error('Alert creation error:', err);
            throw err;
        }
    };

    const deleteAlert = async (id: string) => {
        try {
            const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete alert');
            setAlerts(prev => prev.filter(a => a.id !== id));
            setStates(prev => {
                const next = { ...prev };
                delete next[id];
                return next;
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to delete alert');
            throw err;
        }
    };

    const fetchLogs = async (id: string) => {
        try {
            const res = await fetch(`${API_BASE}/${id}/logs`);
            if (!res.ok) throw new Error('Failed to fetch logs');
            return await res.json();
        } catch (err) {
            console.error(err);
            return [];
        }
    };

    useEffect(() => {
        fetchAlerts();
        // Poll for states every 5 seconds
        const interval = setInterval(() => {
            fetch(API_BASE + '/states')
                .then(res => res.json())
                .then(data => {
                    const statesMap = data.reduce((acc: any, curr: any) => {
                        acc[curr.rule_id] = curr;
                        return acc;
                    }, {});
                    setStates(statesMap);
                })
                .catch(console.error);
        }, 5000);
        return () => clearInterval(interval);
    }, [fetchAlerts]);

    return {
        alerts,
        states,
        loading,
        error,
        fetchAlerts,
        createAlert,
        deleteAlert,
        fetchLogs
    };
}
