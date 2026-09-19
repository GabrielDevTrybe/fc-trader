import {
  BankrollSummary,
  BankrollCapitalSummary,
  BankrollAdjustmentPayload,
  TradingGoal,
  TradingGoalCreatePayload,
  CurrentActionResponse,
  ActionFeedbackPayload,
  MarketOpportunity,
  ObservationBatchItem,
  ObservationBatchResponse,
  Trade,
} from '@/types';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function fetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    cache: 'no-store',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `Erro HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  async getHealth(): Promise<{ status: string; app: string; database_configured: boolean }> {
    const rootUrl = API_BASE_URL.replace('/api/v1', '');
    const res = await fetch(`${rootUrl}/health`);
    if (!res.ok) throw new Error('API offline');
    return res.json();
  },

  // Bankroll & Capital Accounting
  async getBankroll(isPaper: boolean = false): Promise<BankrollSummary> {
    return fetchJson<BankrollSummary>(`/bankroll?is_paper=${isPaper}`);
  },

  async getCapitalSummary(isPaper: boolean = false): Promise<BankrollCapitalSummary> {
    return fetchJson<BankrollCapitalSummary>(`/bankroll/capital?is_paper=${isPaper}`);
  },

  async recordAdjustment(payload: BankrollAdjustmentPayload): Promise<any> {
    return fetchJson<any>('/bankroll/adjustments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async onboardBankroll(payload: { cash_balance: number; target_balance: number }): Promise<BankrollCapitalSummary> {
    return fetchJson<BankrollCapitalSummary>('/bankroll/onboarding', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async syncBankroll(payload: { current_actual_balance: number; reason?: string; is_paper?: boolean }): Promise<any> {
    return fetchJson<any>('/bankroll/sync', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Goals
  async getActiveGoal(isPaper: boolean = false): Promise<TradingGoal | null> {
    return fetchJson<TradingGoal | null>(`/goals/active?is_paper=${isPaper}`);
  },

  async createGoal(payload: TradingGoalCreatePayload): Promise<TradingGoal> {
    return fetchJson<TradingGoal>('/goals', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async completeGoal(goalId: string): Promise<TradingGoal> {
    return fetchJson<TradingGoal>(`/goals/${goalId}/complete`, {
      method: 'POST',
    });
  },

  async closeGoal(goalId: string): Promise<TradingGoal> {
    return fetchJson<TradingGoal>(`/goals/${goalId}/close`, {
      method: 'POST',
    });
  },

  // Action Engine & Feedback
  async getCurrentAction(isPaper: boolean = false): Promise<CurrentActionResponse> {
    return fetchJson<CurrentActionResponse>(`/actions/current?is_paper=${isPaper}`);
  },

  async verifyMarket(isPaper: boolean = false): Promise<CurrentActionResponse> {
    return fetchJson<CurrentActionResponse>(`/actions/verify?is_paper=${isPaper}`, {
      method: 'POST',
    });
  },

  async sendActionFeedback(payload: ActionFeedbackPayload): Promise<any> {
    return fetchJson<any>('/actions/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Market Opportunities & Analysis (Phase 1)
  async getOpportunities(params?: {
    player?: string;
    min_rating?: number;
    min_profit?: number;
    min_roi?: number;
    min_liquidity?: number;
    confidence?: string;
  }): Promise<MarketOpportunity[]> {
    const searchParams = new URLSearchParams();
    if (params?.player) searchParams.set('player', params.player);
    if (params?.min_rating) searchParams.set('min_rating', params.min_rating.toString());
    if (params?.min_profit) searchParams.set('min_profit', params.min_profit.toString());
    if (params?.min_roi) searchParams.set('min_roi', params.min_roi.toString());
    if (params?.min_liquidity) searchParams.set('min_liquidity', params.min_liquidity.toString());
    if (params?.confidence) searchParams.set('confidence', params.confidence);

    const qs = searchParams.toString();
    return fetchJson<MarketOpportunity[]>(`/opportunities${qs ? `?${qs}` : ''}`);
  },

  async recordObservations(items: ObservationBatchItem[]): Promise<ObservationBatchResponse> {
    return fetchJson<ObservationBatchResponse>('/observations', {
      method: 'POST',
      body: JSON.stringify(items),
    });
  },

  async recordObservationsCsv(csvContent: string, dataOrigin: string = 'user'): Promise<ObservationBatchResponse> {
    return fetchJson<ObservationBatchResponse>('/observations/batch/csv', {
      method: 'POST',
      body: JSON.stringify({ csv_content: csvContent, data_origin: dataOrigin }),
    });
  },

  async getCardSnapshots(cardId: string, platform: string = 'console'): Promise<any[]> {
    return fetchJson<any[]>(`/observations/snapshots/${cardId}?platform=${platform}`);
  },

  // Trades
  async getTrades(isPaper?: boolean, status?: string): Promise<Trade[]> {
    const params = new URLSearchParams();
    if (isPaper !== undefined) params.set('is_paper', isPaper.toString());
    if (status) params.set('status', status);
    const qs = params.toString();
    return fetchJson<Trade[]>(`/trades${qs ? `?${qs}` : ''}`);
  },

  async openTrade(
    params: { cardId?: string; playerId?: string; buyPrice: number; isPaper?: boolean } | string,
    legacyBuyPrice?: number,
    legacyIsPaper: boolean = true
  ): Promise<Trade> {
    if (typeof params === 'object') {
      return fetchJson<Trade>('/trades', {
        method: 'POST',
        body: JSON.stringify({
          card_id: params.cardId,
          player_id: params.playerId,
          buy_price: params.buyPrice,
          is_paper_trade: params.isPaper ?? true,
        }),
      });
    }
    return fetchJson<Trade>('/trades', {
      method: 'POST',
      body: JSON.stringify({
        player_id: params,
        buy_price: legacyBuyPrice,
        is_paper_trade: legacyIsPaper,
      }),
    });
  },

  async closeTrade(tradeId: string, sellPrice: number): Promise<Trade> {
    return fetchJson<Trade>(`/trades/${tradeId}/close`, {
      method: 'POST',
      body: JSON.stringify({
        sell_price: sellPrice,
      }),
    });
  },

  // Dev Cleanup (Tests Only)
  async cleanupTestData(): Promise<any> {
    return fetchJson<any>('/dev/cleanup-test-data', {
      method: 'POST',
    });
  },
};
