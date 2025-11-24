'use client';

import {
    ComposedChart,
    Line,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Area
} from 'recharts';
import { format } from 'date-fns';

interface ChartData {
    date: Date;
    close: number;
    sma50?: number;
    sma200?: number;
    upper?: number;
    lower?: number;
}

interface StockChartProps {
    data: ChartData[];
}

export default function StockChart({ data }: StockChartProps) {
    return (
        <div className="h-[400px] w-full bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Price & Indicators</h3>
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                    <XAxis
                        dataKey="date"
                        tickFormatter={(date) => format(new Date(date), 'MMM dd')}
                        minTickGap={30}
                        tick={{ fontSize: 12 }}
                    />
                    <YAxis
                        domain={['auto', 'auto']}
                        tick={{ fontSize: 12 }}
                    />
                    <Tooltip
                        labelFormatter={(label) => format(new Date(label), 'MMM dd, yyyy')}
                        contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }}
                    />
                    <Legend />

                    {/* Bollinger Bands Area */}
                    <Area
                        type="monotone"
                        dataKey="upper"
                        stroke="none"
                        fill="#93c5fd"
                        fillOpacity={0.1}
                    />
                    <Area
                        type="monotone"
                        dataKey="lower"
                        stroke="none"
                        fill="#93c5fd"
                        fillOpacity={0.1}
                    />

                    {/* Price Line */}
                    <Line
                        type="monotone"
                        dataKey="close"
                        stroke="#2563eb"
                        strokeWidth={2}
                        dot={false}
                        name="Price"
                    />

                    {/* SMAs */}
                    <Line
                        type="monotone"
                        dataKey="sma50"
                        stroke="#16a34a"
                        strokeWidth={1.5}
                        dot={false}
                        name="SMA 50"
                    />
                    <Line
                        type="monotone"
                        dataKey="sma200"
                        stroke="#dc2626"
                        strokeWidth={1.5}
                        dot={false}
                        name="SMA 200"
                    />
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
}
