export type StrategyType = 'QUICK_FLIP' | 'SWING' | 'INVESTMENT';

export interface Player {
  id: string;
  name: string;
  rating?: number | null;
  position?: string | null;
  rarity?: string | null;
  league?: string | null;
  club?: string | null;
  nation?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CardExternalId {
  id: string;
  card_id: string;
  provider: string;
  external_id: string;
  created_at: string;
}

export interface PlayerCard {
  id: string;
  player_id: string;
  player_name?: string | null;
  game_version: string;
  rating: number;
  position?: string | null;
  rarity?: string | null;
  club?: string | null;
  league?: string | null;
  nation?: string | null;
  is_active: boolean;
  external_ids?: CardExternalId[];
  created_at: string;
  updated_at: string;
}

export interface MarketOpportunity {
  id: string;
  card_id: string;
  player_id?: string | null;
  card?: PlayerCard | null;
  player?: Player | null;
  platform: string;
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
  card_id: string;
  player_id?: string | null;
  card?: PlayerCard | null;
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
  trading_goal_id?: string | null;
  action_recommendation_id?: string | null;
  data_origin?: string;
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

export interface BankrollCapitalSummary {
  total_equity: number;
  cash_balance: number;
  available_cash: number;
  inventory_cost: number;
  open_positions_count: number;
  total_trading_profit: number;
  total_external_rewards: number;
  total_external_expenses: number;
  total_reconciliations: number;
  total_external_adjustments: number;
  is_configured: boolean;
  is_paper: boolean;
}

export interface BankrollAdjustmentPayload {
  amount: number;
  adjustment_type: 'reward' | 'external_purchase' | 'manual_correction';
  reason?: string;
  is_paper: boolean;
}

export interface BankrollOnboardingPayload {
  cash_balance: number;
  target_balance: number;
}

export interface BankrollSyncPayload {
  current_actual_balance: number;
  reason?: string;
  is_paper?: boolean;
}

export interface TradingGoal {
  id: string;
  starting_balance: number;
  target_balance: number;
  current_balance: number;
  status: 'ACTIVE' | 'COMPLETED' | 'CLOSED';
  is_paper: boolean;
  data_origin: string;
  started_at: string;
  completed_at?: string | null;
  closed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
  progress_percentage: number;
  trades_count: number;
  profit_in_goal: number;
  win_rate: number | null;
}

export interface TradingGoalCreatePayload {
  target_balance: number;
  starting_balance?: number;
  is_paper: boolean;
}

export interface PurchaseItem {
  buy_price: number;
}

export interface ActionFeedbackPayload {
  recommendation_id: string;
  action_result: 'BOUGHT' | 'MISSED' | 'CANCELLED';
  purchases?: PurchaseItem[];
  missed_reason?: string | null;
  notes?: string | null;
}

export interface MarketSnapshot {
  id: string;
  card_id: string;
  platform: string;
  sample_count: number;
  valid_sample_count: number;
  min_price?: number | null;
  max_price?: number | null;
  median_price?: number | null;
  p20_price?: number | null;
  p80_price?: number | null;
  robust_mean?: number | null;
  std_dev: number;
  dispersion_ratio: number;
  estimated_market_price?: number | null;
  conservative_buy_price?: number | null;
  conservative_sell_price?: number | null;
  confidence_score: number;
  confidence_level: string;
  freshness_status: string;
  newest_observation_age_seconds?: number | null;
  trend: string;
  data_quality: string;
  calculated_at: string;
  expires_at?: string | null;
  data_origin: string;
}

export interface ActionRecommendation {
  id: string;
  card_id: string;
  player_id?: string | null;
  trading_goal_id?: string | null;
  opportunity_id?: string | null;
  market_snapshot_id?: string | null;
  action_type: string;
  strategy_name: string;
  strategy_type?: StrategyType | string;
  player_name: string;
  player_rating: number;

  // Identidade Inequívoca da Versão da Carta
  card_version_name?: string | null;
  card_club?: string | null;
  card_league?: string | null;
  card_position?: string | null;
  card_platform?: string | null;

  max_buy_price: number;
  target_sell_price: number;
  recommended_quantity: number;
  capital_limit: number;
  estimated_profit_per_card: number;
  estimated_total_profit: number;
  estimated_roi: number;
  profit_at_max_buy?: number | null;
  roi_at_max_buy?: number | null;
  capital_efficiency?: number | null;
  expected_holding_time_minutes?: number | null;
  snapshot_market_price: number;
  snapshot_observed_price: number;
  snapshot_liquidity_score: number;
  snapshot_confidence: string;
  snapshot_opportunity_score: number;
  snapshot_sample_count: number;
  snapshot_available_cash: number;
  market_data_age_seconds?: number | null;
  no_action_reason_code?: string | null;
  why_explanation: string;
  urgency: string;
  status: string;
  is_paper: boolean;
  data_origin: string;
  created_at: string;
  expires_at: string;
}

export interface CurrentActionResponse {
  has_action: boolean;
  status: 'ACTION_AVAILABLE' | 'NO_ACTION' | 'GOAL_INACTIVE' | 'BANKROLL_NOT_CONFIGURED' | 'INSUFFICIENT_DATA';
  action?: ActionRecommendation | null;
  title?: string | null;
  message?: string | null;
  suggestion?: string | null;
  no_action_reason_code?: string | null;
}

export interface OpportunityAnalysis {
  card_id: string;
  player_id: string;
  player_name: string;
  rating: number;
  version_name?: string | null;
  club?: string | null;
  platform: string;
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

export interface ObservationBatchItem {
  player: string;
  rating: number;
  price: number;
  type: string;
  position?: string;
  rarity?: string;
  league?: string;
  club?: string;
  nation?: string;
  platform?: string;
  card_id?: string;
  external_card_id?: string;
  provider?: string;
  data_origin?: string;
  observed_at?: string;
}
