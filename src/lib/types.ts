export type Exchange = 'NSE' | 'BSE';

export interface Instrument {
  id: string;
  symbol: string;
  exchange: Exchange;
  name: string;
  sector?: string;
  lastPrice?: number;
}

export interface Quote {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
}

export interface IndicatorSnapshot {
  symbol: string;
  timestamp: number;
  rsi: number;
  sma50: number;
  sma200: number;
  macd: {
    macd: number;
    signal: number;
    histogram: number;
  };
  bollinger: {
    upper: number;
    middle: number;
    lower: number;
  };
  volume20Avg: number;
}

export type DipClass = 'Micro' | 'Minor' | 'Moderate' | 'Significant' | 'Major' | 'None';

export interface DipSnapshot {
  symbol: string;
  timestamp: number;
  currentPrice: number;
  high52Week: number;
  dipPercent: number;
  dipClass: DipClass;
}

export interface PreScoreRule {
  id: string;
  label: string;
  points: number;
  met: boolean;
}

export interface PreScore {
  symbol: string;
  timestamp: number;
  total: number; // 0-12
  rules: PreScoreRule[];
}

export interface Checklist {
  symbol: string;
  timestamp: number;
  q1_macro: boolean | 'unsure'; // +2 if true
  q2_financials: boolean | 'unsure'; // +2 if true
  q3_management: boolean | 'unsure'; // +2 if true
  q4_support: boolean | 'unsure'; // +2 if true
  notes?: string;
}

export type AllocationBand = 'High Conviction' | 'Strong' | 'Moderate' | 'Weak' | 'Skip';

export interface FinalScore {
  symbol: string;
  timestamp: number;
  preScore: number;
  checklistScore: number;
  totalScore: number; // 0-20
  band: AllocationBand;
}

export interface Watchlist {
  id: string;
  name: string;
  instruments: Instrument[];
  createdAt: number;
}

export interface JournalEntry {
  id: string;
  symbol: string;
  timestamp: number;
  action: 'Buy' | 'Skip' | 'Wait';
  price: number;
  preScore: number;
  finalScore: number;
  allocationBand: AllocationBand;
  notes?: string;
}

// Fundamentals Suggestion Types (LLM-Assisted)
export interface Citation {
  url: string;
  title: string;
  published_at?: string;
  snippet?: string;
}

export interface QuestionSuggestion {
  rec: string;
  confidence: 'High' | 'Medium' | 'Low';
  reasons: string[];
  citations: Citation[];
}

export interface FundamentalsSuggestionResponse {
  q1: QuestionSuggestion;  // Dip cause
  q2: QuestionSuggestion;  // Earnings resilience
  q3: QuestionSuggestion;  // Management/guidance
  q4: QuestionSuggestion;  // Support level
  summary: string;
  generated_at: string;
  model_version: string;
  cache_key?: string;
}
