import { api } from '@/lib/api';
import StockChart from '@/components/StockChart';
import { calculateSMA, calculateBollingerBands } from '@/lib/indicators';
import Link from 'next/link';
import { ArrowLeft, TrendingUp, TrendingDown, Activity, BarChart3, Info, CheckCircle2, Circle } from 'lucide-react';
import ChecklistPanel from '@/components/ChecklistPanel';
import clsx from 'clsx';
import { calculatePreScoreWithVolume } from '@/lib/scoring';
import { DipSnapshot, IndicatorSnapshot } from '@/lib/types';

// Helper to calculate indicators for time series (chart only)
function calculateTimeSeriesIndicators(history: any[]) {
    const closes = history.map(h => h.close);

    return history.map((point, index) => {
        const slice = closes.slice(0, index + 1);
        return {
            date: point.date,
            close: point.close,
            sma50: calculateSMA(slice, 50) || undefined,
            sma200: calculateSMA(slice, 200) || undefined,
            upper: calculateBollingerBands(slice).upper || undefined,
            lower: calculateBollingerBands(slice).lower || undefined,
        };
    });
}

function StatCard({ label, value, color, tooltip }: { label: string, value: string | number, color?: string, tooltip: string }) {
    return (
        <div className="glass-card p-4 relative group">
            <div className="flex items-center gap-1 text-sm text-gray-500 mb-1">
                {label}
                <div className="relative">
                    <Info className="w-3 h-3 cursor-help text-gray-400 hover:text-primary" />
                    {/* Tooltip */}
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 pointer-events-none">
                        {tooltip}
                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                    </div>
                </div>
            </div>
            <div className={clsx("text-xl font-bold truncate", color || "text-gray-900 dark:text-white")}>
                {value}
            </div>
        </div>
    );
}

export default async function StockPage({ params }: { params: Promise<{ symbol: string }> }) {
    const { symbol: rawSymbol } = await params;
    const symbol = decodeURIComponent(rawSymbol);

    let barsData = null;
    let dipAnalysis = null;
    let indicatorsData = null;
    let insightData = null;
    let error = null;

    try {
        // Parallel fetch for faster loading
        const [fullAnalysis, insight] = await Promise.all([
            api.getFullAnalysis(symbol, '1y'),
            api.getLatestInsight(symbol)
        ]);

        const data = fullAnalysis;
        barsData = { bars: data.bars };
        dipAnalysis = data.dip_analysis;
        indicatorsData = data.indicators;
        insightData = insight;

    } catch (err) {
        console.error("Error fetching stock data:", err);
        error = "Failed to load stock data. Please try again.";
    }

    if (error || (!barsData && !dipAnalysis && !indicatorsData)) {
        return (
            <div className="min-h-screen flex items-center justify-center p-8 text-center">
                <div className="glass-card p-8 max-w-md">
                    <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Activity className="w-8 h-8 text-gray-400" />
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Stock Not Found</h2>
                    <p className="text-gray-500 mb-6">We couldn't fetch data for <span className="font-mono font-bold">{symbol}</span>. {error}</p>
                    <Link href="/" className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-indigo-600 transition-colors">
                        Return to Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    // Transform bars for chart
    const history = barsData?.bars?.map((b: any) => ({
        date: b.t,
        open: b.o,
        high: b.h,
        low: b.l,
        close: b.c,
        volume: b.v
    })) || [];

    const chartData = calculateTimeSeriesIndicators(history);

    // Prepare PreScore object for ChecklistPanel (adapter)
    const preScoreForChecklist = {
        symbol,
        timestamp: Date.now(),
        total: insightData?.pre_score?.total || 0,
        rules: insightData?.pre_score?.components?.map((c: any) => ({
            id: c.name,
            label: c.name,
            points: c.points,
            met: c.points > 0
        })) || []
    };

    return (
        <div className="min-h-screen p-4 md:p-8 pb-24 space-y-6">
            {/* Header */}
            <header className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors">
                        <ArrowLeft className="w-6 h-6" />
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">{symbol}</h1>
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                            <span>NSE Equity</span>
                            <span>•</span>
                            <span>{dipAnalysis?.dip_class} Dip</span>
                            {insightData?.state === 'insufficient_data' && (
                                <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200">
                                    Insufficient Data
                                </span>
                            )}
                        </div>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-3xl font-bold font-mono">
                        ₹{dipAnalysis?.current_price?.toFixed(2)}
                    </div>
                    <div className={clsx(
                        "flex items-center justify-end gap-1 font-medium",
                        (dipAnalysis?.dip_pct || 0) > 0 ? "text-red-500" : "text-green-500"
                    )}>
                        {(dipAnalysis?.dip_pct || 0) > 0 ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                        <span>{dipAnalysis?.dip_pct?.toFixed(2)}% from 52W High</span>
                    </div>
                </div>
            </header>

            {/* Main Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Left Column: Chart & Stats & Insight Cards */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Chart Card */}
                    <div className="glass-card p-6 h-[500px]">
                        <StockChart data={chartData} />
                    </div>

                    {/* Insight Cards (LLM Generated) */}
                    {insightData?.insight_cards?.length > 0 && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {insightData.insight_cards.map((card: any, idx: number) => (
                                <div key={idx} className={clsx(
                                    "glass-card p-5 border-l-4",
                                    card.severity === 'warning' ? "border-l-amber-500" :
                                        card.severity === 'critical' ? "border-l-red-500" : "border-l-blue-500"
                                )}>
                                    <h3 className="font-semibold text-lg mb-2 flex items-center gap-2">
                                        {card.severity === 'warning' ? <TrendingDown className="w-5 h-5 text-amber-500" /> :
                                            card.severity === 'critical' ? <Activity className="w-5 h-5 text-red-500" /> :
                                                <Info className="w-5 h-5 text-blue-500" />}
                                        {card.title}
                                    </h3>
                                    <ul className="space-y-1.5">
                                        {card.bullets.map((bullet: string, bIdx: number) => (
                                            <li key={bIdx} className="text-sm text-gray-600 dark:text-gray-300 flex items-start gap-2">
                                                <span className="mt-1.5 w-1 h-1 rounded-full bg-gray-400 flex-shrink-0" />
                                                {bullet}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                        <StatCard
                            label="RSI (14)"
                            value={indicatorsData?.rsi?.toFixed(2) || 'N/A'}
                            color={(indicatorsData?.rsi || 0) < 30 ? "text-green-500" : (indicatorsData?.rsi || 0) > 70 ? "text-red-500" : undefined}
                            tooltip="The Relative Strength Index (RSI) measures the speed and change of price movements. Values above 70 indicate the stock is 'overbought' (potentially expensive), while values below 30 indicate it is 'oversold' (potentially cheap). It's a primary gauge for trend reversal."
                        />
                        <StatCard
                            label="MACD Histogram"
                            value={indicatorsData?.macd?.histogram?.toFixed(2) || 'N/A'}
                            color={(indicatorsData?.macd?.histogram || 0) > 0 ? "text-green-500" : "text-red-500"}
                            tooltip="The Moving Average Convergence Divergence (MACD) Histogram shows the difference between the MACD line and the Signal line. Positive bars indicate bullish momentum (price rising), while negative bars indicate bearish momentum (price falling). Growing bars suggest the trend is strengthening."
                        />
                        <StatCard
                            label="Dip Depth"
                            value={dipAnalysis?.dip_pct ? `${dipAnalysis.dip_pct.toFixed(2)}%` : 'N/A'}
                            color={(dipAnalysis?.dip_pct || 0) > 15 ? "text-green-500" : undefined}
                            tooltip="The percentage decline from the 52-week high. We categorize dips as: Micro (<5%), Minor (5-10%), Moderate (10-20%), Significant (20-40%), and Major (>40%). Deeper dips offer more value but carry higher trend risk."
                        />
                        <StatCard
                            label="52W High"
                            value={`₹${dipAnalysis?.high_52w?.toFixed(2) || 'N/A'}`}
                            tooltip="The highest price the stock has traded at in the last 52 weeks. This serves as a major psychological resistance level. The 'Dip' is calculated as the percentage decline from this peak."
                        />
                        <StatCard
                            label="Days from High"
                            value={dipAnalysis?.days_from_high || 'N/A'}
                            tooltip="The number of days since the stock last touched its 52-week high. A low number suggests recent strength or a fresh correction. A high number (>200) indicates a prolonged downtrend or consolidation phase."
                        />
                        <StatCard
                            label="SMA 50"
                            value={`₹${indicatorsData?.sma50?.toFixed(2) || 'N/A'}`}
                            color={(dipAnalysis?.current_price || 0) > (indicatorsData?.sma50 || 0) ? "text-green-500" : "text-red-500"}
                            tooltip="The 50-Day Simple Moving Average represents the intermediate-term trend. It often acts as a dynamic support level in uptrends. If the price is above this line, the stock is generally considered to be in a healthy short-term uptrend."
                        />
                        <StatCard
                            label="SMA 200"
                            value={`₹${indicatorsData?.sma200?.toFixed(2) || 'N/A'}`}
                            color={(dipAnalysis?.current_price || 0) > (indicatorsData?.sma200 || 0) ? "text-green-500" : "text-red-500"}
                            tooltip="The 200-Day Simple Moving Average is the gold standard for long-term trend direction. Institutional investors use this to define Bull vs. Bear markets. Price above = Bullish; Price below = Bearish."
                        />
                        <StatCard
                            label="Bollinger Upper"
                            value={`₹${indicatorsData?.bollinger?.upper?.toFixed(2) || 'N/A'}`}
                            color={(dipAnalysis?.current_price || 0) >= (indicatorsData?.bollinger?.upper || Infinity) ? "text-red-500" : undefined}
                            tooltip="The Upper Bollinger Band represents two standard deviations above the 20-day average. When price touches or exceeds this, it is statistically 'expensive' or overextended to the upside, often preceding a pullback."
                        />
                        <StatCard
                            label="Bollinger Lower"
                            value={`₹${indicatorsData?.bollinger?.lower?.toFixed(2) || 'N/A'}`}
                            color={(dipAnalysis?.current_price || 0) <= (indicatorsData?.bollinger?.lower || -Infinity) ? "text-green-500" : undefined}
                            tooltip="The Lower Bollinger Band represents two standard deviations below the 20-day average. When price touches or falls below this, it is statistically 'cheap' or oversold, often preceding a bounce."
                        />
                        <StatCard
                            label="Vol (20D Avg)"
                            value={indicatorsData?.volume_avg ? (indicatorsData.volume_avg / 1000000).toFixed(2) + 'M' : 'N/A'}
                            color={(barsData?.bars?.[barsData.bars.length - 1]?.v || 0) > (indicatorsData?.volume_avg || 0) ? "text-green-500" : undefined}
                            tooltip="The average number of shares traded daily over the last 20 trading days. High relative volume confirms the validity of a price move (breakout or breakdown), while low volume suggests a lack of conviction."
                        />
                    </div>
                </div>

                {/* Right Column: Scoring & Checklist */}
                <div className="space-y-6">
                    {/* Pre-Score Card */}
                    <div className="glass-card p-6 relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-10">
                            <BarChart3 className="w-24 h-24" />
                        </div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Activity className="w-5 h-5 text-primary" />
                            Pre-Score Analysis
                        </h3>

                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <div className="text-4xl font-bold text-primary">
                                    {insightData?.pre_score?.total || 0}<span className="text-xl text-gray-400">/12</span>
                                </div>
                                <div className="text-sm text-gray-500">Technical Score</div>
                            </div>
                            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                                <TrendingUp className="w-6 h-6 text-primary" />
                            </div>
                        </div>

                        <div className="space-y-3">
                            {insightData?.pre_score?.components?.map((comp: any, idx: number) => (
                                <div key={idx} className="flex flex-col p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                                    <div className="flex items-center justify-between mb-1">
                                        <div className="flex items-center gap-2">
                                            {comp.points > 0 ? (
                                                <CheckCircle2 className="w-4 h-4 text-green-500" />
                                            ) : (
                                                <Circle className="w-4 h-4 text-gray-300" />
                                            )}
                                            <span className={clsx("text-sm", comp.points > 0 ? "text-gray-900 dark:text-white font-medium" : "text-gray-500")}>
                                                {comp.name}
                                            </span>
                                        </div>
                                        {comp.points > 0 && (
                                            <span className="text-xs font-bold text-green-600 bg-green-100 dark:bg-green-900/30 px-2 py-0.5 rounded">
                                                +{comp.points}
                                            </span>
                                        )}
                                    </div>
                                    {/* Evidence text from LLM/Backend */}
                                    <div className="text-xs text-gray-500 pl-6">
                                        {comp.evidence}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Checklist Panel */}
                    <ChecklistPanel
                        symbol={symbol}
                        preScore={preScoreForChecklist}
                        questions={insightData?.checklist_prompts?.map((p: any) => ({
                            id: p.id,
                            text: p.text,
                            points: 2
                        }))}
                    />

                    {/* Disclaimer */}
                    <div className="text-xs text-gray-400 text-center px-4">
                        {insightData?.disclaimer}
                    </div>
                </div>
            </div>
        </div>
    );
}
