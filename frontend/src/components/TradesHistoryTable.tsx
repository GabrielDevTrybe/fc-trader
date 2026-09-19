'use client';

import React from 'react';
import { Trade } from '@/types';
import { CheckCircle2, Clock, DollarSign } from 'lucide-react';

interface TradesHistoryTableProps {
  trades: Trade[];
  loading: boolean;
  onCloseTrade: (trade: Trade) => void;
}

export const TradesHistoryTable: React.FC<TradesHistoryTableProps> = ({
  trades,
  loading,
  onCloseTrade,
}) => {
  return (
    <div className="table-card">
      <div className="table-header-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <DollarSign size={16} color="var(--accent-green)" />
          <span style={{ fontWeight: 800, letterSpacing: '0.5px' }}>OPERAÇÕES & PAPER TRADING</span>
          <span className="badge cyan">{trades.length} REGISTRADAS</span>
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>STATUS</th>
              <th>PLAYER</th>
              <th>MODALIDADE</th>
              <th>COMPRA</th>
              <th>VENDA</th>
              <th>TAXA (5%)</th>
              <th>LÍQUIDO</th>
              <th>LUCRO</th>
              <th>ROI</th>
              <th>AÇÕES</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} className="empty-state">
                  Carregando operações...
                </td>
              </tr>
            ) : trades.length === 0 ? (
              <tr>
                <td colSpan={10} className="empty-state">
                  Nenhum trade registrado ainda. Simule compras a partir das oportunidades vivas.
                </td>
              </tr>
            ) : (
              trades.map((t) => {
                const isOpen = t.status === 'open';
                const profitFormatted =
                  t.profit !== null && t.profit !== undefined
                    ? t.profit >= 0
                      ? `+${t.profit.toLocaleString('pt-BR')}`
                      : t.profit.toLocaleString('pt-BR')
                    : '-';
                const roiFormatted =
                  t.roi !== null && t.roi !== undefined ? `${(t.roi * 100).toFixed(1)}%` : '-';

                return (
                  <tr key={t.id}>
                    <td>
                      <span className={`badge ${isOpen ? 'gold' : 'green'}`}>
                        {isOpen ? 'ABERTO' : 'VENDIDO'}
                      </span>
                    </td>
                    <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                      {t.card?.player_name || t.player?.name || 'Jogador'} ({t.card?.rating || t.player?.rating || '-'}) {t.card?.club ? `• ${t.card.club}` : ''}
                    </td>
                    <td>
                      <span className={`badge ${t.is_paper_trade ? 'cyan' : 'gold'}`}>
                        {t.is_paper_trade ? 'PAPER' : 'REAL'}
                      </span>
                    </td>
                    <td className="mono">{t.buy_price.toLocaleString('pt-BR')}</td>
                    <td className="mono">{t.sell_price ? t.sell_price.toLocaleString('pt-BR') : '-'}</td>
                    <td className="mono" style={{ color: 'var(--accent-red)' }}>
                      {t.tax ? `-${t.tax.toLocaleString('pt-BR')}` : '-'}
                    </td>
                    <td className="mono">{t.net_received ? t.net_received.toLocaleString('pt-BR') : '-'}</td>
                    <td
                      className="mono"
                      style={{
                        fontWeight: 700,
                        color: (t.profit || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                      }}
                    >
                      {profitFormatted}
                    </td>
                    <td className="mono" style={{ color: 'var(--accent-green)' }}>
                      {roiFormatted}
                    </td>
                    <td>
                      {isOpen && (
                        <button
                          onClick={() => onCloseTrade(t)}
                          className="btn-terminal primary"
                          style={{ padding: '4px 10px', fontSize: '11px' }}
                        >
                          Vender (Fechar)
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
