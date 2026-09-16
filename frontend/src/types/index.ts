export interface Player {
  id: string;
  name: string;
  rating: number;
  position?: string | null;
  rarity?: string | null;
  league?: string | null;
  club?: string | null;
  nation?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MarketOpportunity {
  id: string;
  player_id: string;
  player: Player;
  observed_price: number;
  market_price: number;
  max_buy_price: number;
  target_sell_price: number;
  estimated_profit: number;
  roi: number;
  confidence: 'LOW' | 'MEDIUM' | 'HIGH';
  liquidity_score: number;
  opportunity_score: number;
  detected_at: string;
  expires_at?: string | null;
}

export interface Trade {
  id: string;
  player_id: string;
  player?: Player | null;
  buy_price: number;
  sell_price?: number | null;
  tax?: number | null;
  net_received?: number | null;
  profit?: number | null;
  roi?: number | null;
  bought_at: string;
  sold_at?: string | null;
  status: 'open' | 'sold' | 'cancelled';
  is_paper_trade: boolean;
  created_at: string;
}

export interface BankrollMilestone {
  target: number;
  label: string;
  achieved: boolean;
  progress_percentage: number;
}

export interface BankrollSummary {
  balance: number;
  initial_bankroll: number;
  profit_today: number;
  total_profit: number;
  total_trades: number;
  win_rate: number | null;
  average_roi: number | null;
  next_target: number;
  milestones: BankrollMilestone[];
  is_paper: boolean;
}

export interface ObservationBatchItem {
  player: string;
  rating: number;
  price: number;
  type: 'buy_now' | 'bid' | 'sale_estimate';
  position?: string;
  rarity?: string;
  league?: string;
  club?: string;
  nation?: string;
}

export interface OpportunityAnalysis {
  player_id: string;
  player_name: string;
  rating: number;
  observed_price: number;
  market_price: number | null;
  max_buy_price: number;
  target_sell_price: number;
  expected_profit: number;
  expected_roi: number;
  confidence: string;
  liquidity_score: number;
  opportunity_score: number;
  recommendation: string;
  reason: string;
}

export interface ObservationBatchResponse {
  processed_count: number;
  analyses: OpportunityAnalysis[];
}
