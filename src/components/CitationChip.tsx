'use client';

import { Citation } from '@/lib/types';
import { ExternalLink } from 'lucide-react';

interface CitationChipProps {
  citation: Citation;
  index: number;
}

export default function CitationChip({ citation, index }: CitationChipProps) {
  const formatDate = (dateString?: string) => {
    if (!dateString) return null;

    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return '1 day ago';
      if (diffDays < 7) return `${diffDays} days ago`;
      if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
      return date.toLocaleDateString();
    } catch {
      return null;
    }
  };

  const freshness = formatDate(citation.published_at);
  const isRecent = citation.published_at && formatDate(citation.published_at)?.includes('day');

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors border border-gray-200 dark:border-gray-700 group"
    >
      <span className="font-medium text-gray-700 dark:text-gray-300">
        [{index + 1}]
      </span>
      <span className="text-gray-600 dark:text-gray-400 truncate max-w-[200px]">
        {citation.title}
      </span>
      {freshness && (
        <span className={`text-xs ${isRecent ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500'}`}>
          • {freshness}
        </span>
      )}
      <ExternalLink className="w-3 h-3 text-gray-400 group-hover:text-indigo-500 transition-colors" />
    </a>
  );
}
