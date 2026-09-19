'use client';

import React, { useState } from 'react';
import { BankrollCapitalSummary } from '@/types';
import { BankrollAdjustmentModal } from './BankrollAdjustmentModal';
import { BankrollSyncModal } from './BankrollSyncModal';
import { Wallet, Landmark, Layers, TrendingUp, PlusCircle, RefreshCw, Scale } from 'lucide-react';

interface BankrollCapitalCardProps {
  capital: BankrollCapitalSummary | null;
  loading: boolean;
  isPaper: boolean;
  onRefresh: () => void;
}

export const BankrollCapitalCard: React.FC<BankrollCapitalCardProps> = ({
  capital,
  loading,
  isPaper,
  onRefresh,
}) => {
  const [isAdjustmentModalOpen, setIsAdjustmentModalOpen] = useState(false);
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);

  return (
    <div style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Balanço Patrimonial & Caixa ({isPaper ? 'Paper Trading' : 'Banca Real'})
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setIsSyncModalOpen(true)}
            className="btn-terminal"
            style={{ fontSize: '11px', padding: '4px 10px', borderColor: 'rgba(56, 189, 248, 0.4)', color: 'var(--accent-cyan)' }}
            id="btn-open-sync"
            title="Reconciliar saldo com o jogo sem poluir o lucro de trade"
          >
            <Scale size={13} />
            <span>Sincronizar Saldo Real</span>
          </button>
          <button
            onClick={() => setIsAdjustmentModalOpen(true)}
            className="btn-terminal"
            style={{ fontSize: '11px', padding: '4px 10px' }}
            id="btn-open-adjustment"
          >
            <PlusCircle size={13} />
            <span>Ajustar Recompensas</span>
          </button>
        </div>
      </div>

      <div className="capital-grid">
        {/* Patrimônio Total */}
        <div className="capital-tile highlight">
          <div className="tile-title">
            <Landmark size={14} style={{ color: 'var(--accent-green)' }} />
            <span>Patrimônio Total (Equity)</span>
          </div>
          <div className="tile-amount" style={{ color: 'var(--accent-green)' }}>
            {(capital?.total_equity || 0).toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="tile-subtitle">
            Caixa + Custo do Estoque Aberto
          </div>
        </div>

        {/* Moedas em Caixa Disponíveis */}
        <div className="capital-tile">
          <div className="tile-title">
            <Wallet size={14} style={{ color: 'var(--accent-gold)' }} />
            <span>Moedas em Caixa (Disponível)</span>
          </div>
          <div className="tile-amount" style={{ color: 'var(--accent-gold)' }}>
            {(capital?.cash_balance || 0).toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="tile-subtitle">
            Pronto para compras imediatas
          </div>
        </div>

        {/* Cartas em Aberto / Estoque */}
        <div className="capital-tile">
          <div className="tile-title">
            <Layers size={14} style={{ color: 'var(--accent-cyan)' }} />
            <span>Custo em Estoque</span>
          </div>
          <div className="tile-amount" style={{ color: 'var(--accent-cyan)' }}>
            {(capital?.inventory_cost || 0).toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="tile-subtitle">
            {capital?.open_positions_count || 0} carta(s) aguardando venda
          </div>
        </div>

        {/* Lucro de Trading Realizado */}
        <div className="capital-tile">
          <div className="tile-title">
            <TrendingUp size={14} style={{ color: (capital?.total_trading_profit || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }} />
            <span>Lucro Líquido Realizado</span>
          </div>
          <div
            className="tile-amount"
            style={{ color: (capital?.total_trading_profit || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}
          >
            {(capital?.total_trading_profit || 0) >= 0 ? '+' : ''}
            {(capital?.total_trading_profit || 0).toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="tile-subtitle">
            Ganhos estritos de operações
          </div>
        </div>
      </div>

      {/* Linha de Detalhamento Contábil Transparente */}
      {capital && (capital.total_reconciliations !== 0 || capital.total_external_rewards !== 0 || capital.total_external_expenses !== 0) && (
        <div style={{ display: 'flex', gap: '16px', marginTop: '10px', fontSize: '11px', color: 'var(--text-muted)', flexWrap: 'wrap', background: 'rgba(15, 23, 42, 0.4)', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
          <div>
            <span>Reconciliações Manuais: </span>
            <strong style={{ color: capital.total_reconciliations >= 0 ? 'var(--accent-cyan)' : 'var(--accent-red)' }}>
              {capital.total_reconciliations >= 0 ? '+' : ''}{capital.total_reconciliations.toLocaleString()} coins
            </strong>
          </div>
          <div>
            <span>Recompensas do Jogo: </span>
            <strong style={{ color: 'var(--accent-green)' }}>
              +{capital.total_external_rewards.toLocaleString()} coins
            </strong>
          </div>
          <div>
            <span>Gastos Externos: </span>
            <strong style={{ color: 'var(--accent-red)' }}>
              {capital.total_external_expenses.toLocaleString()} coins
            </strong>
          </div>
        </div>
      )}

      <BankrollAdjustmentModal
        isOpen={isAdjustmentModalOpen}
        isPaper={isPaper}
        onClose={() => setIsAdjustmentModalOpen(false)}
        onSuccess={onRefresh}
      />

      <BankrollSyncModal
        isOpen={isSyncModalOpen}
        currentTrackedBalance={capital?.cash_balance || 0}
        isPaper={isPaper}
        onClose={() => setIsSyncModalOpen(false)}
        onSuccess={onRefresh}
      />
    </div>
  );
};
