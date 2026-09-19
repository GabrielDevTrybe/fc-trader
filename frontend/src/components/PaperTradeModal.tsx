'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { MarketOpportunity, Trade } from '@/types';
import { X, CheckCircle, Play } from 'lucide-react';

interface PaperTradeModalProps {
  isOpen: boolean;
  opportunity: MarketOpportunity | null;
  tradeToClose: Trade | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const PaperTradeModal: React.FC<PaperTradeModalProps> = ({
  isOpen,
  opportunity,
  tradeToClose,
  onClose,
  onSuccess,
}) => {
  const [loading, setLoading] = useState(false);
  const [buyPrice, setBuyPrice] = useState(opportunity ? opportunity.observed_price.toString() : '600');
  const [sellPrice, setSellPrice] = useState(tradeToClose?.sell_price?.toString() || '1050');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const isClosing = Boolean(tradeToClose);

  const handleOpenTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!opportunity) return;
    setLoading(true);
    setErrorMessage(null);

    try {
      await api.openTrade({
        cardId: opportunity.card_id,
        playerId: opportunity.player_id ?? undefined,
        buyPrice: parseInt(buyPrice, 10),
        isPaper: true,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Erro ao abrir Paper Trade');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tradeToClose) return;
    setLoading(true);
    setErrorMessage(null);

    try {
      await api.closeTrade(tradeToClose.id, parseInt(sellPrice, 10));
      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Erro ao fechar Paper Trade');
    } finally {
      setLoading(false);
    }
  };

  // Preview de cálculos determinísticos
  const parsedSell = parseInt(sellPrice, 10) || 0;
  const netPreview = Math.floor(parsedSell * 0.95);
  const taxPreview = parsedSell - netPreview;
  const cost = tradeToClose ? tradeToClose.buy_price : parseInt(buyPrice, 10) || 0;
  const profitPreview = netPreview - cost;
  const roiPreview = cost > 0 ? ((profitPreview / cost) * 100).toFixed(1) : '0';

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '480px' }}>
        <div className="modal-header">
          <div style={{ fontWeight: 700, fontSize: '15px' }}>
            {isClosing ? 'FECHAR PAPER TRADE (VENDA)' : 'SIMULAR PAPER TRADE (COMPRA)'}
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={isClosing ? handleCloseTrade : handleOpenTrade}>
          <div className="modal-body">
            {errorMessage && (
              <div style={{ background: 'var(--accent-red-glow)', border: '1px solid var(--accent-red)', padding: '10px', borderRadius: '6px', fontSize: '12px' }}>
                {errorMessage}
              </div>
            )}

            {!isClosing && opportunity && (
              <>
                <div style={{ padding: '10px', background: 'var(--bg-surface-elevated)', borderRadius: '8px' }}>
                  <div style={{ fontWeight: 700, fontSize: '14px' }}>
                    {opportunity.card?.player_name || opportunity.player?.name || 'Carta'} {opportunity.card?.rating || opportunity.player?.rating ? `(${opportunity.card?.rating || opportunity.player?.rating})` : ''}
                    {opportunity.card?.rarity ? ` • ${opportunity.card.rarity}` : ''}
                    {opportunity.card?.club ? ` • ${opportunity.card.club}` : ''}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Mercado: {opportunity.market_price.toLocaleString('pt-BR')} | Alvo Venda: {opportunity.target_sell_price.toLocaleString('pt-BR')} | Plataforma: {opportunity.platform?.toUpperCase() || 'CONSOLE'}
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Preço de Compra (Coins)</label>
                  <input
                    className="input-terminal"
                    type="number"
                    value={buyPrice}
                    onChange={(e) => setBuyPrice(e.target.value)}
                    required
                  />
                </div>
              </>
            )}

            {isClosing && tradeToClose && (
              <>
                <div style={{ padding: '10px', background: 'var(--bg-surface-elevated)', borderRadius: '8px' }}>
                  <div style={{ fontWeight: 700, fontSize: '14px' }}>
                    {tradeToClose.card?.player_name || tradeToClose.player?.name || 'Carta'} {tradeToClose.card?.rating || tradeToClose.player?.rating ? `(${tradeToClose.card?.rating || tradeToClose.player?.rating})` : ''}
                    {tradeToClose.card?.club ? ` • ${tradeToClose.card.club}` : ''}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Comprado por: {tradeToClose.buy_price.toLocaleString('pt-BR')} coins
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Preço de Venda Executado (Coins)</label>
                  <input
                    className="input-terminal"
                    type="number"
                    value={sellPrice}
                    onChange={(e) => setSellPrice(e.target.value)}
                    min="1"
                    step="1"
                    required
                  />
                </div>

                {/* Preview de Taxa e Lucro Real */}
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '12px', borderRadius: '8px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Taxa EA FC (5%):</span>
                    <span className="mono" style={{ color: 'var(--accent-red)' }}>-{taxPreview} coins</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Valor Líquido Recebido:</span>
                    <span className="mono">{netPreview.toLocaleString('pt-BR')} coins</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, paddingTop: '6px', borderTop: '1px solid var(--border-subtle)' }}>
                    <span>Lucro Líquido Estimado:</span>
                    <span className="mono" style={{ color: profitPreview >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                      {profitPreview >= 0 ? `+${profitPreview}` : profitPreview} coins ({roiPreview}%)
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn-terminal">
              Cancelar
            </button>
            <button type="submit" disabled={loading} className="btn-terminal primary">
              <Play size={13} />
              <span>{loading ? 'Confirmando...' : isClosing ? 'Confirmar Venda' : 'Simular Compra'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
