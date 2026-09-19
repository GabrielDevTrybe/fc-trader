'use client';

import React, { useState } from 'react';
import { Trade } from '@/types';
import { api } from '@/lib/api';
import { Package, ArrowUpRight, DollarSign, X } from 'lucide-react';

interface OpenPositionsListProps {
  trades: Trade[];
  loading: boolean;
  onRefresh: () => void;
}

export const OpenPositionsList: React.FC<OpenPositionsListProps> = ({
  trades,
  loading,
  onRefresh,
}) => {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [sellPrice, setSellPrice] = useState<number>(1000);
  const [selling, setSelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openTrades = trades.filter((t) => t.status === 'open');

  const handleOpenSellModal = (trade: Trade) => {
    setSelectedTrade(trade);
    // Sugestão de venda: compra + 20% ou pelo menos cobrindo taxa EA
    const suggestedSell = Math.ceil(trade.buy_price * 1.25 / 50) * 50;
    setSellPrice(suggestedSell);
  };

  const handleConfirmSell = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTrade) return;
    setSelling(true);
    setError(null);

    try {
      await api.closeTrade(selectedTrade.id, sellPrice);
      setSelectedTrade(null);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Erro ao registrar venda');
    } finally {
      setSelling(false);
    }
  };

  if (openTrades.length === 0) {
    return null;
  }

  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Package size={18} style={{ color: 'var(--accent-cyan)' }} />
          <h3 style={{ fontSize: '15px', fontWeight: '800' }}>
            Posições Abertas em Estoque ({openTrades.length})
          </h3>
        </div>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          Cartas compradas aguardando venda no mercado
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
        {openTrades.map((t) => (
          <div
            key={t.id}
            style={{
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '10px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontWeight: '800', color: '#fff', fontSize: '15px' }}>
                  {t.card?.player_name || t.player?.name || 'Jogador'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Rating: {t.card?.rating || t.player?.rating || '--'} • {t.card?.rarity || 'Gold'} {t.card?.position || t.player?.position ? `• ${t.card?.position || t.player?.position}` : ''} {t.card?.club ? `• ${t.card.club}` : ''}
                </div>
              </div>
              <span className="badge green" style={{ fontSize: '11px' }}>
                ABERTO
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Preço de Compra:</span>
              <span className="mono" style={{ fontWeight: '700', color: 'var(--accent-gold)' }}>
                {t.buy_price.toLocaleString()} coins
              </span>
            </div>

            <button
              onClick={() => handleOpenSellModal(t)}
              className="btn-terminal"
              style={{
                width: '100%',
                justifyContent: 'center',
                background: 'rgba(6, 182, 212, 0.12)',
                borderColor: 'rgba(6, 182, 212, 0.3)',
                color: 'var(--accent-cyan)',
                fontWeight: '700',
              }}
            >
              <ArrowUpRight size={14} />
              <span>Registrar Venda</span>
            </button>
          </div>
        ))}
      </div>

      {/* Modal para Registrar Venda */}
      {selectedTrade && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <DollarSign size={18} style={{ color: 'var(--accent-green)' }} />
                <h3 style={{ fontSize: '16px', fontWeight: '800' }}>Registrar Venda da Carta</h3>
              </div>
              <button onClick={() => setSelectedTrade(null)} className="btn-terminal" style={{ padding: '4px' }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleConfirmSell}>
              <div className="modal-body">
                {error && (
                  <div style={{ background: 'var(--accent-red-glow)', color: 'var(--accent-red)', padding: '10px 14px', borderRadius: '8px', fontSize: '13px' }}>
                    {error}
                  </div>
                )}

                <div style={{ background: 'var(--bg-surface-elevated)', padding: '12px 16px', borderRadius: '8px', fontSize: '13px' }}>
                  <div style={{ fontWeight: '700', color: '#fff' }}>{selectedTrade.player?.name}</div>
                  <div style={{ color: 'var(--text-muted)' }}>
                    Comprado por: <strong className="mono">{selectedTrade.buy_price.toLocaleString()} coins</strong>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Preço Efetivo de Venda:</label>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    className="input-terminal mono"
                    value={sellPrice}
                    onChange={(e) => setSellPrice(parseInt(e.target.value, 10) || 0)}
                    required
                  />
                </div>

                {/* Cálculo instantâneo do lucro com taxa EA */}
                {(() => {
                  const eaTax = Math.floor(sellPrice * 0.05);
                  const net = sellPrice - eaTax;
                  const profit = net - selectedTrade.buy_price;
                  const roi = ((profit / selectedTrade.buy_price) * 100).toFixed(1);
                  return (
                    <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '8px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                        <span>Taxa EA (5%):</span>
                        <span className="mono" style={{ color: 'var(--accent-red)' }}>- {eaTax.toLocaleString()} coins</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                        <span>Recebido Líquido:</span>
                        <span className="mono">{net.toLocaleString()} coins</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', fontWeight: '700' }}>
                        <span>Lucro Realizado:</span>
                        <span className="mono" style={{ color: profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                          {profit >= 0 ? '+' : ''}{profit.toLocaleString()} coins ({roi}%)
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </div>

              <div className="modal-footer">
                <button type="button" onClick={() => setSelectedTrade(null)} className="btn-terminal">
                  Cancelar
                </button>
                <button type="submit" disabled={selling} className="btn-terminal primary" style={{ background: 'var(--accent-green)', color: '#fff', fontWeight: '700' }}>
                  {selling ? 'Salvando...' : 'Confirmar Venda'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
