'use client';

import React from 'react';
import { BankrollSummary } from '@/types';
import { TrendingUp, Target, Award, DollarSign } from 'lucide-react';

interface BankrollCardProps {
  summary: BankrollSummary | null;
  loading: boolean;
}

export const BankrollCard: React.FC<BankrollCardProps> = ({ summary, loading }) => {
  const balance = summary ? summary.balance : 5000;
  const profitToday = summary ? summary.profit_today : 0;
  const totalProfit = summary ? summary.total_profit : 0;
  const nextTarget = summary ? summary.next_target : 10000;
  const winRate = summary?.win_rate !== null && summary?.win_rate !== undefined ? `${summary.win_rate}%` : '-';
  const avgRoi = summary?.average_roi !== null && summary?.average_roi !== undefined ? `${summary.average_roi}%` : '-';

  return (
    <div className="metrics-grid">
      <div className="metric-card gold">
        <div className="metric-label">BANKROLL ATUAL</div>
        <div className="metric-value">
          {balance.toLocaleString('pt-BR')} <span style={{ fontSize: '14px', color: 'var(--accent-gold)' }}>COINS</span>
        </div>
        <div className="metric-sub">
          <DollarSign size={13} color="var(--accent-gold)" />
          <span>Inicial: {(summary?.initial_bankroll || 5000).toLocaleString('pt-BR')}</span>
        </div>
      </div>

      <div className="metric-card green">
        <div className="metric-label">PROFIT HOJE</div>
        <div className="metric-value" style={{ color: profitToday >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
          {profitToday >= 0 ? `+${profitToday.toLocaleString('pt-BR')}` : profitToday.toLocaleString('pt-BR')}
        </div>
        <div className="metric-sub">
          <TrendingUp size={13} color="var(--accent-green)" />
          <span>Total: {totalProfit >= 0 ? `+${totalProfit.toLocaleString('pt-BR')}` : totalProfit.toLocaleString('pt-BR')}</span>
        </div>
      </div>

      <div className="metric-card cyan">
        <div className="metric-label">WIN RATE / ROI MÉDIO</div>
        <div className="metric-value" style={{ fontSize: '22px' }}>
          {winRate} <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>/ {avgRoi}</span>
        </div>
        <div className="metric-sub">
          <Award size={13} color="var(--accent-cyan)" />
          <span>Trades Concluídos: {summary?.total_trades || 0}</span>
        </div>
      </div>

      <div className="metric-card">
        <div className="metric-label">PRÓXIMA META</div>
        <div className="metric-value" style={{ color: 'var(--accent-gold)' }}>
          {nextTarget.toLocaleString('pt-BR')}
        </div>
        <div className="metric-sub">
          <Target size={13} color="var(--text-muted)" />
          <span>Faltam: {Math.max(0, nextTarget - balance).toLocaleString('pt-BR')} coins</span>
        </div>
      </div>
    </div>
  );
};
