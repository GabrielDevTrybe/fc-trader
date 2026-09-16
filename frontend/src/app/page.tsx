'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { BankrollSummary, MarketOpportunity, Trade } from '@/types';
import { Header } from '@/components/Header';
import { BankrollCard } from '@/components/BankrollCard';
import { MilestoneProgress } from '@/components/MilestoneProgress';
import { LiveOpportunitiesTable } from '@/components/LiveOpportunitiesTable';
import { TradesHistoryTable } from '@/components/TradesHistoryTable';
import { QuickObservationModal } from '@/components/QuickObservationModal';
import { PaperTradeModal } from '@/components/PaperTradeModal';
import { Search, Filter, RefreshCw } from 'lucide-react';

export default function DashboardPage() {
  const [apiConnected, setApiConnected] = useState(false);
  const [isPaperMode, setIsPaperMode] = useState(true);
  const [loading, setLoading] = useState(true);

  const [bankrollSummary, setBankrollSummary] = useState<BankrollSummary | null>(null);
  const [opportunities, setOpportunities] = useState<MarketOpportunity[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);

  // Filter state
  const [playerFilter, setPlayerFilter] = useState('');
  const [minRatingFilter, setMinRatingFilter] = useState('');
  const [minProfitFilter, setMinProfitFilter] = useState('');

  // Modals state
  const [isQuickEntryOpen, setIsQuickEntryOpen] = useState(false);
  const [isPaperTradeModalOpen, setIsPaperTradeModalOpen] = useState(false);
  const [selectedOppForTrade, setSelectedOppForTrade] = useState<MarketOpportunity | null>(null);
  const [tradeToClose, setTradeToClose] = useState<Trade | null>(null);

  const loadData = useCallback(async () => {
    try {
      // 1. Health check
      try {
        await api.getHealth();
        setApiConnected(true);
      } catch {
        setApiConnected(false);
      }

      // 2. Bankroll
      const bSummary = await api.getBankroll(isPaperMode);
      setBankrollSummary(bSummary);

      // 3. Opportunities
      const opps = await api.getOpportunities({
        player: playerFilter.trim() || undefined,
        min_rating: minRatingFilter ? parseInt(minRatingFilter, 10) : undefined,
        min_profit: minProfitFilter ? parseInt(minProfitFilter, 10) : undefined,
      });
      setOpportunities(opps);

      // 4. Trades
      const tList = await api.getTrades(isPaperMode);
      setTrades(tList);
    } catch (err) {
      console.error('Falha ao carregar dados do dashboard:', err);
    } finally {
      setLoading(false);
    }
  }, [isPaperMode, playerFilter, minRatingFilter, minProfitFilter]);

  // Initial load and polling
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Polling simples a cada 5s
    return () => clearInterval(interval);
  }, [loadData]);

  const handleOpenTradeModal = (opp: MarketOpportunity) => {
    setSelectedOppForTrade(opp);
    setTradeToClose(null);
    setIsPaperTradeModalOpen(true);
  };

  const handleCloseTradeModal = (trade: Trade) => {
    setSelectedOppForTrade(null);
    setTradeToClose(trade);
    setIsPaperTradeModalOpen(true);
  };

  return (
    <main className="container">
      <Header
        apiConnected={apiConnected}
        isPaperMode={isPaperMode}
        onTogglePaperMode={(paper) => setIsPaperMode(paper)}
        onOpenQuickEntry={() => setIsQuickEntryOpen(true)}
      />

      {/* Métricas de Banca */}
      <BankrollCard summary={bankrollSummary} loading={loading} />

      {/* Progressão de Metas */}
      {bankrollSummary && (
        <MilestoneProgress
          milestones={bankrollSummary.milestones}
          currentBalance={bankrollSummary.balance}
        />
      )}

      {/* Barra de Filtros e Busca */}
      <div className="actions-bar">
        <div className="search-filter-group">
          <div style={{ position: 'relative', flex: 2 }}>
            <input
              className="input-terminal"
              placeholder="Buscar jogador (ex: Palhinha)..."
              value={playerFilter}
              onChange={(e) => setPlayerFilter(e.target.value)}
              style={{ paddingLeft: '34px' }}
            />
            <Search
              size={15}
              style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
            />
          </div>

          <input
            className="input-terminal"
            type="number"
            placeholder="Min Rating (ex: 80)"
            value={minRatingFilter}
            onChange={(e) => setMinRatingFilter(e.target.value)}
            style={{ flex: 1 }}
          />

          <input
            className="input-terminal"
            type="number"
            placeholder="Min Profit (coins)"
            value={minProfitFilter}
            onChange={(e) => setMinProfitFilter(e.target.value)}
            style={{ flex: 1 }}
          />
        </div>

        <button onClick={loadData} className="btn-terminal" title="Atualizar dados agora">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Atualizar</span>
        </button>
      </div>

      {/* Tabela de Oportunidades Vivas */}
      <LiveOpportunitiesTable
        opportunities={opportunities}
        loading={loading}
        onOpenTrade={handleOpenTradeModal}
      />

      {/* Histórico de Trades e Paper Trading */}
      <TradesHistoryTable
        trades={trades}
        loading={loading}
        onCloseTrade={handleCloseTradeModal}
      />

      {/* Modais */}
      <QuickObservationModal
        isOpen={isQuickEntryOpen}
        onClose={() => setIsQuickEntryOpen(false)}
        onSuccess={loadData}
      />

      <PaperTradeModal
        isOpen={isPaperTradeModalOpen}
        opportunity={selectedOppForTrade}
        tradeToClose={tradeToClose}
        onClose={() => setIsPaperTradeModalOpen(false)}
        onSuccess={loadData}
      />
    </main>
  );
}
