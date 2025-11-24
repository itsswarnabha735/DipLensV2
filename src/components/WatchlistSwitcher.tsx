'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { FolderOpen, Plus, Edit2, Trash2, Check, X } from 'lucide-react';
import clsx from 'clsx';

export default function WatchlistSwitcher() {
    const watchlists = useAppStore((state) => state.watchlists);
    const activeWatchlistId = useAppStore((state) => state.activeWatchlistId);
    const setActiveWatchlist = useAppStore((state) => state.setActiveWatchlist);
    const createWatchlist = useAppStore((state) => state.createWatchlist);
    const renameWatchlist = useAppStore((state) => state.renameWatchlist);
    const deleteWatchlist = useAppStore((state) => state.deleteWatchlist);

    const [isOpen, setIsOpen] = useState(false);
    const [creatingNew, setCreatingNew] = useState(false);
    const [newName, setNewName] = useState('');
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');

    const activeWatchlist = watchlists.find(wl => wl.id === activeWatchlistId);

    const handleCreate = () => {
        if (newName.trim()) {
            createWatchlist(newName.trim());
            setNewName('');
            setCreatingNew(false);
        }
    };

    const handleRename = (id: string) => {
        if (editName.trim()) {
            renameWatchlist(id, editName.trim());
            setEditingId(null);
            setEditName('');
        }
    };

    const handleDelete = (id: string, name: string) => {
        if (confirm(`Are you sure you want to delete the watchlist "${name}"? All stocks in this watchlist will be removed.`)) {
            deleteWatchlist(id);
        }
    };

    const startEdit = (id: string, currentName: string) => {
        setEditingId(id);
        setEditName(currentName);
    };

    return (
        <div className="relative">
            {/* Active Watchlist Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 px-4 py-2.5 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary dark:hover:border-primary transition-all shadow-sm hover:shadow-md"
            >
                <FolderOpen className="w-5 h-5 text-primary" />
                <div className="text-left">
                    <div className="text-sm font-bold text-gray-900 dark:text-white">
                        {activeWatchlist?.name || 'No Watchlist'}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                        {activeWatchlist?.instruments.length || 0} stocks
                    </div>
                </div>
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-40"
                        onClick={() => setIsOpen(false)}
                    />

                    {/* Dropdown Content */}
                    <div className="absolute top-full mt-2 right-0 w-72 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-xl z-50 overflow-hidden">
                        <div className="p-2 border-b border-gray-200 dark:border-gray-700">
                            <div className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 px-2 py-1 font-semibold">
                                Your Watchlists
                            </div>
                        </div>

                        {/* Watchlist Items */}
                        <div className="max-h-64 overflow-y-auto custom-scrollbar p-2 space-y-1">
                            {watchlists.map((wl) => (
                                <div
                                    key={wl.id}
                                    className={clsx(
                                        "group relative rounded-lg transition-all",
                                        wl.id === activeWatchlistId
                                            ? "bg-primary/10 border border-primary/30"
                                            : "hover:bg-gray-50 dark:hover:bg-gray-700/50"
                                    )}
                                >
                                    {editingId === wl.id ? (
                                        // Edit Mode
                                        <div className="flex items-center gap-2 p-2">
                                            <input
                                                type="text"
                                                value={editName}
                                                onChange={(e) => setEditName(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleRename(wl.id);
                                                    if (e.key === 'Escape') setEditingId(null);
                                                }}
                                                className="flex-1 px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                                                autoFocus
                                            />
                                            <button
                                                onClick={() => handleRename(wl.id)}
                                                className="p-1 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded"
                                            >
                                                <Check className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => setEditingId(null)}
                                                className="p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ) : (
                                        // Display Mode
                                        <div className="flex items-center justify-between p-2">
                                            <button
                                                onClick={() => {
                                                    setActiveWatchlist(wl.id);
                                                    setIsOpen(false);
                                                }}
                                                className="flex-1 text-left"
                                            >
                                                <div className="font-medium text-sm text-gray-900 dark:text-white">
                                                    {wl.name}
                                                </div>
                                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                                    {wl.instruments.length} stocks
                                                </div>
                                            </button>
                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => startEdit(wl.id, wl.name)}
                                                    className="p-1.5 text-gray-400 hover:text-primary hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                                                    title="Rename"
                                                >
                                                    <Edit2 className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(wl.id, wl.name)}
                                                    className="p-1.5 text-gray-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded transition-colors"
                                                    title="Delete"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Create New Watchlist */}
                        <div className="p-2 border-t border-gray-200 dark:border-gray-700">
                            {creatingNew ? (
                                <div className="flex items-center gap-2">
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') handleCreate();
                                            if (e.key === 'Escape') {
                                                setCreatingNew(false);
                                                setNewName('');
                                            }
                                        }}
                                        placeholder="Watchlist name..."
                                        className="flex-1 px-2 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
                                        autoFocus
                                    />
                                    <button
                                        onClick={handleCreate}
                                        className="p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded"
                                    >
                                        <Check className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => {
                                            setCreatingNew(false);
                                            setNewName('');
                                        }}
                                        className="p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setCreatingNew(true)}
                                    className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10 rounded-lg transition-colors"
                                >
                                    <Plus className="w-4 h-4" />
                                    Create New Watchlist
                                </button>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
