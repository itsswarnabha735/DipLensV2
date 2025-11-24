'use client';

import { useAppStore } from '@/lib/store';
import { useMarketData } from '@/hooks/useMarketData';
import WatchlistInput from '@/components/WatchlistInput';
import WatchlistSwitcher from '@/components/WatchlistSwitcher';
import TickerCard from '@/components/TickerCard';
import { RefreshCw, BookOpen, BarChart2, Bell, Zap } from 'lucide-react';
import { calculateDip } from '@/lib/indicators';
import Link from 'next/link';

export default function Dashboard() {
  const { refresh } = useMarketData();
  const watchlists = useAppStore((state) => state.watchlists);
  const activeWatchlistId = useAppStore((state) => state.activeWatchlistId);
  const quotes = useAppStore((state) => state.quotes);
  const dips = useAppStore((state) => state.dips);
  const preScores = useAppStore((state) => state.preScores);

  // Get active watchlist instruments
  const activeWatchlist = watchlists.find(wl => wl.id === activeWatchlistId);
  const instruments = activeWatchlist?.instruments || [];

  return (
    <div className="min-h-screen p-4 md:p-8 pb-20">
      <div className="max-w-7xl mx-auto space-y-12">

        {/* Header / Hero */}
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="text-center md:text-left">
            <h1 className="text-5xl md:text-6xl font-black tracking-tighter mb-2">
              <span className="text-gray-900 dark:text-white">Dip</span>
              <span className="text-gradient">Lens</span>
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-lg font-medium">
              Institutional-grade dip scoring for retail investors.
            </p>
          </div>

          <div className="flex items-center gap-4 bg-white/50 dark:bg-gray-800/50 backdrop-blur-md p-2 rounded-full border border-gray-200/50 dark:border-gray-700/50 shadow-sm">
            <Link
              href="/sectors-radar"
              className="p-3 text-gray-500 hover:text-primary hover:bg-primary/10 transition-all rounded-full"
              title="Sector Analysis"
            >
              <BarChart2 className="w-6 h-6" />
            </Link>
            <Link
              href="/journal"
              className="p-3 text-gray-500 hover:text-primary hover:bg-primary/10 transition-all rounded-full"
              title="Decision Journal"
            >
              <BookOpen className="w-6 h-6" />
            </Link>
            <Link
              href="/alerts"
              className="p-3 text-gray-500 hover:text-primary hover:bg-primary/10 transition-all rounded-full"
              title="Alerts Center"
            >
              <Bell className="w-6 h-6" />
            </Link>
            <div className="w-px h-8 bg-gray-300 dark:bg-gray-700 mx-1"></div>
            <button
              onClick={() => refresh()}
              className="p-3 text-gray-500 hover:text-primary hover:bg-primary/10 transition-all rounded-full group"
              title="Refresh Data"
            >
              <RefreshCw className="w-6 h-6 group-hover:rotate-180 transition-transform duration-500" />
            </button>
          </div>
        </div>

        {/* Search & Watchlist Input */}
        <div className="max-w-2xl mx-auto relative z-20">
          <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full opacity-20 animate-pulse-slow pointer-events-none"></div>
          <WatchlistInput />
        </div>

        {/* Watchlist Grid */}
        <div className="space-y-6">
          <div className="flex items-center justify-between gap-3 mb-6">
            <div className="flex items-center gap-3">
              <Zap className="w-6 h-6 text-amber-500 fill-amber-500" />
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
                {activeWatchlist?.name || 'Watchlist'}
              </h2>
              <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 text-xs font-bold rounded-full border border-gray-200 dark:border-gray-700">
                {instruments.length}
              </span>
            </div>

            {/* Watchlist Switcher */}
            <WatchlistSwitcher />
          </div>

          {instruments.length === 0 ? (
            <div className="text-center py-24 glass rounded-3xl border-dashed border-2 border-gray-300 dark:border-gray-700">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <BarChart2 className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Your watchlist is empty</h3>
              <p className="text-gray-500 max-w-md mx-auto">
                Search for a stock symbol above (e.g., <span className="font-mono bg-gray-100 dark:bg-gray-800 px-1 rounded">RELIANCE.NS</span>) to start tracking dips.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {instruments.map((item) => {
                const quote = quotes[item.symbol];
                const dip = dips[item.symbol];
                const preScore = preScores[item.symbol];

                return (
                  <TickerCard
                    key={item.symbol}
                    instrument={item}
                    quote={quote}
                    preScore={preScore}
                    dipClass={dip?.dipClass}
                    dipPercent={dip?.dipPercent}
                    loading={!quote}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
