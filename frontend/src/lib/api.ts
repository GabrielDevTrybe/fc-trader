import {
  BankrollSummary,
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
    ...options,
    headers: {
      'Content-Type': 'application/json',
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

  async getBankroll(isPaper: boolean = false): Promise<BankrollSummary> {
    return fetchJson<BankrollSummary>(`/bankroll?is_paper=${isPaper}`);
  },

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

  async getTrades(isPaper?: boolean): Promise<Trade[]> {
    const qs = isPaper !== undefined ? `?is_paper=${isPaper}` : '';
    return fetchJson<Trade[]>(`/trades${qs}`);
  },

  async openTrade(playerId: string, buyPrice: number, isPaper: boolean = true): Promise<Trade> {
    return fetchJson<Trade>('/trades', {
      method: 'POST',
      body: JSON.stringify({
        player_id: playerId,
        buy_price: buyPrice,
        is_paper_trade: isPaper,
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
};
