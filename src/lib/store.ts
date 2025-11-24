import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Instrument, Quote, PreScore, FinalScore, DipSnapshot, JournalEntry, Watchlist } from './types';
import { nanoid } from 'nanoid';

interface AppState {
    // Legacy field for migration
    watchlist?: Instrument[];

    // New watchlist structure
    watchlists: Watchlist[];
    activeWatchlistId: string | null;

    quotes: Record<string, Quote>;
    dips: Record<string, DipSnapshot>;
    preScores: Record<string, PreScore>;
    finalScores: Record<string, FinalScore>;
    journal: JournalEntry[];

    // Watchlist management
    createWatchlist: (name: string) => string;
    renameWatchlist: (id: string, name: string) => void;
    deleteWatchlist: (id: string) => void;
    setActiveWatchlist: (id: string) => void;

    // Stock management (updated to use watchlist ID)
    addToWatchlist: (watchlistId: string, instrument: Instrument) => void;
    removeFromWatchlist: (watchlistId: string, symbol: string) => void;

    // Legacy methods for compatibility
    addToActiveWatchlist: (instrument: Instrument) => void;
    removeFromActiveWatchlist: (symbol: string) => void;

    updateQuote: (quote: Quote) => void;
    updateDip: (dip: DipSnapshot) => void;
    updatePreScore: (score: PreScore) => void;
    updateFinalScore: (score: FinalScore) => void;
    addJournalEntry: (entry: JournalEntry) => void;
}

export const useAppStore = create<AppState>()(
    persist(
        (set, get) => ({
            watchlists: [],
            activeWatchlistId: null,
            quotes: {},
            dips: {},
            preScores: {},
            finalScores: {},
            journal: [],

            createWatchlist: (name) => {
                const id = nanoid();
                const newWatchlist: Watchlist = {
                    id,
                    name,
                    instruments: [],
                    createdAt: Date.now(),
                };
                set((state) => ({
                    watchlists: [...state.watchlists, newWatchlist],
                    activeWatchlistId: id,
                }));
                return id;
            },

            renameWatchlist: (id, name) =>
                set((state) => ({
                    watchlists: state.watchlists.map((wl) =>
                        wl.id === id ? { ...wl, name } : wl
                    ),
                })),

            deleteWatchlist: (id) =>
                set((state) => {
                    const newWatchlists = state.watchlists.filter((wl) => wl.id !== id);

                    // If deleting active watchlist, switch to first available
                    let newActiveId = state.activeWatchlistId;
                    if (state.activeWatchlistId === id) {
                        newActiveId = newWatchlists.length > 0 ? newWatchlists[0].id : null;
                    }

                    // If no watchlists left, create a default one
                    if (newWatchlists.length === 0) {
                        const defaultId = nanoid();
                        const defaultWatchlist: Watchlist = {
                            id: defaultId,
                            name: 'Default',
                            instruments: [],
                            createdAt: Date.now(),
                        };
                        return {
                            watchlists: [defaultWatchlist],
                            activeWatchlistId: defaultId,
                        };
                    }

                    return {
                        watchlists: newWatchlists,
                        activeWatchlistId: newActiveId,
                    };
                }),

            setActiveWatchlist: (id) =>
                set({ activeWatchlistId: id }),

            addToWatchlist: (watchlistId, instrument) =>
                set((state) => ({
                    watchlists: state.watchlists.map((wl) => {
                        if (wl.id !== watchlistId) return wl;
                        if (wl.instruments.some((i) => i.symbol === instrument.symbol)) return wl;
                        return { ...wl, instruments: [...wl.instruments, instrument] };
                    }),
                })),

            removeFromWatchlist: (watchlistId, symbol) =>
                set((state) => {
                    const newWatchlists = state.watchlists.map((wl) => {
                        if (wl.id !== watchlistId) return wl;
                        return { ...wl, instruments: wl.instruments.filter((i) => i.symbol !== symbol) };
                    });

                    // Auto-delete empty watchlists (except if it's the last one)
                    const filteredWatchlists = newWatchlists.filter(
                        (wl) => wl.instruments.length > 0 || newWatchlists.length === 1
                    );

                    // If active watchlist was auto-deleted, switch to first available
                    let newActiveId = state.activeWatchlistId;
                    if (!filteredWatchlists.find(wl => wl.id === state.activeWatchlistId)) {
                        newActiveId = filteredWatchlists.length > 0 ? filteredWatchlists[0].id : null;
                    }

                    return {
                        watchlists: filteredWatchlists,
                        activeWatchlistId: newActiveId,
                    };
                }),

            // Legacy compatibility methods
            addToActiveWatchlist: (instrument) => {
                const state = get();
                if (state.activeWatchlistId) {
                    get().addToWatchlist(state.activeWatchlistId, instrument);
                }
            },

            removeFromActiveWatchlist: (symbol) => {
                const state = get();
                if (state.activeWatchlistId) {
                    get().removeFromWatchlist(state.activeWatchlistId, symbol);
                }
            },

            updateQuote: (quote) =>
                set((state) => ({
                    quotes: { ...state.quotes, [quote.symbol]: quote },
                })),

            updateDip: (dip) =>
                set((state) => ({
                    dips: { ...state.dips, [dip.symbol]: dip },
                })),

            updatePreScore: (score) =>
                set((state) => ({
                    preScores: { ...state.preScores, [score.symbol]: score },
                }),
                ),

            updateFinalScore: (score) =>
                set((state) => ({
                    finalScores: { ...state.finalScores, [score.symbol]: score },
                })),

            addJournalEntry: (entry) =>
                set((state) => ({
                    journal: [entry, ...state.journal],
                })),
        }),
        {
            name: 'diplens-storage',
            version: 2, // Increment version for migration
            migrate: (persistedState: any, version: number) => {
                if (version < 2) {
                    // Migration from v1 to v2: Convert old watchlist to new structure
                    const oldWatchlist = persistedState.watchlist || [];
                    const defaultId = nanoid();
                    const defaultWatchlist: Watchlist = {
                        id: defaultId,
                        name: 'Default',
                        instruments: oldWatchlist,
                        createdAt: Date.now(),
                    };

                    return {
                        ...persistedState,
                        watchlist: undefined, // Remove old field
                        watchlists: [defaultWatchlist],
                        activeWatchlistId: defaultId,
                    };
                }
                return persistedState as AppState;
            },
        }
    )
);
