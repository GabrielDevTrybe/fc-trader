'use client';

import React from 'react';
import { ActionRecommendation } from '@/types';
import { X, ShieldCheck, CheckCircle2, Info, AlertTriangle } from 'lucide-react';

interface WhyExplanationModalProps {
  isOpen: boolean;
  action: ActionRecommendation | null;
  onClose: () => void;
}

export const WhyExplanationModal: React.FC<WhyExplanationModalProps> = ({
  isOpen,
  action,
  onClose,
}) => {
  if (!isOpen || !action) return null;

  const eaTax = Math.floor(action.target_sell_price * 0.05);
  const netPerCard = action.target_sell_price - eaTax;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '640px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck size={22} style={{ color: 'var(--accent-cyan)' }} />
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '800' }}>Racional Matemático da Operação</h3>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Auditoria determinística sem especulação
              </div>
            </div>
          </div>
          <button onClick={onClose} className="btn-terminal" style={{ padding: '4px' }}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Card Resumo do Jogador */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface-elevated)', padding: '14px 18px', borderRadius: '10px' }}>
            <div>
              <div style={{ fontSize: '18px', fontWeight: '800', color: '#fff' }}>
                {action.player_name} ({action.player_rating})
              </div>
              <div style={{ fontSize: '12px', color: 'var(--accent-cyan)', marginTop: '2px', fontWeight: '600' }}>
                Estratégia: {action.strategy_name}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Confiança</div>
              <span className={`badge ${action.snapshot_confidence === 'HIGH' ? 'green' : 'gold'}`}>
                {action.snapshot_confidence} ({action.snapshot_sample_count} observações)
              </span>
            </div>
          </div>

          {/* Decomposição do Cálculo de Preço e Margem */}
          <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '16px' }}>
            <h4 style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '12px', letterSpacing: '0.5px' }}>
              Decomposição Contábil (Por Carta)
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Preço Justo de Mercado (PJM):</span>
                <span className="mono" style={{ fontWeight: '700' }}>~{action.snapshot_market_price.toLocaleString()} coins</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Preço Alvo de Venda:</span>
                <span className="mono" style={{ fontWeight: '700', color: 'var(--accent-cyan)' }}>{action.target_sell_price.toLocaleString()} coins</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Taxa Oficial EA (5%):</span>
                <span className="mono" style={{ color: 'var(--accent-red)' }}>- {eaTax.toLocaleString()} coins</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed var(--border-subtle)', paddingTop: '6px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Líquido Recebido na Venda:</span>
                <span className="mono" style={{ fontWeight: '700' }}>{netPerCard.toLocaleString()} coins</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Teto Máximo de Compra (max_buy):</span>
                <span className="mono" style={{ fontWeight: '700', color: 'var(--accent-gold)' }}>{action.max_buy_price.toLocaleString()} coins</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', fontSize: '14px' }}>
                <span style={{ fontWeight: '700', color: '#fff' }}>Lucro Mínimo Estimado no Teto / Carta:</span>
                <span className="mono" style={{ fontWeight: '800', color: 'var(--accent-green)' }}>
                  +{(action.profit_at_max_buy ?? action.estimated_profit_per_card).toLocaleString()} coins ({((action.roi_at_max_buy ?? action.estimated_roi) * 100).toFixed(1)}% ROI)
                </span>
              </div>
              {action.snapshot_observed_price !== undefined && action.snapshot_observed_price !== null && action.snapshot_observed_price < action.max_buy_price && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)', paddingTop: '4px' }}>
                  <span>Na cotação recente ({action.snapshot_observed_price.toLocaleString()} coins):</span>
                  <span className="mono" style={{ color: 'var(--text-secondary)' }}>
                    +{action.estimated_profit_per_card.toLocaleString()} coins ({(action.estimated_roi * 100).toFixed(1)}% ROI)
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Racional Textual da Engine */}
          <div style={{ background: 'rgba(6, 182, 212, 0.05)', borderLeft: '3px solid var(--accent-cyan)', padding: '14px 16px', borderRadius: '0 8px 8px 0' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--accent-cyan)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Info size={14} />
              <span>Explicação Auditada do ActionEngine</span>
            </div>
            <p style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: '1.5' }}>
              {action.why_explanation}
            </p>
          </div>

          {/* Guardrails e Risco */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px' }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ color: 'var(--text-muted)' }}>Score de Liquidez</div>
              <div className="mono" style={{ fontSize: '15px', fontWeight: '700', color: '#fff', marginTop: '2px' }}>
                {action.snapshot_liquidity_score} / 100
              </div>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ color: 'var(--text-muted)' }}>Limite de Risco Alocado</div>
              <div className="mono" style={{ fontSize: '15px', fontWeight: '700', color: '#fff', marginTop: '2px' }}>
                Até {action.capital_limit.toLocaleString()} coins
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn-terminal primary" style={{ width: '100%' }}>
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
