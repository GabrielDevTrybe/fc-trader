'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { BankrollAdjustmentPayload } from '@/types';
import { X, Coins, Gift, ShoppingBag, Sliders } from 'lucide-react';

interface BankrollAdjustmentModalProps {
  isOpen: boolean;
  isPaper: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const BankrollAdjustmentModal: React.FC<BankrollAdjustmentModalProps> = ({
  isOpen,
  isPaper,
  onClose,
  onSuccess,
}) => {
  const [adjustmentType, setAdjustmentType] = useState<'reward' | 'external_purchase' | 'manual_correction'>('reward');
  const [amount, setAmount] = useState<number>(1000);
  const [reason, setReason] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Ajusta o sinal: compra externa subtrai da banca
    let finalAmount = Math.abs(amount);
    if (adjustmentType === 'external_purchase') {
      finalAmount = -finalAmount;
    }

    try {
      const payload: BankrollAdjustmentPayload = {
        amount: finalAmount,
        adjustment_type: adjustmentType,
        reason: reason.trim() || undefined,
        is_paper: isPaper,
      };

      await api.recordAdjustment(payload);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Erro ao registrar ajuste');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '460px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Coins size={18} style={{ color: 'var(--accent-gold)' }} />
            <h3 style={{ fontSize: '16px', fontWeight: '800' }}>Ajuste de Moedas / Recompensas</h3>
          </div>
          <button onClick={onClose} className="btn-terminal" style={{ padding: '4px' }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ background: 'var(--accent-red-glow)', color: 'var(--accent-red)', padding: '10px 14px', borderRadius: '8px', fontSize: '13px' }}>
                {error}
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Tipo de Movimentação Externa:</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setAdjustmentType('reward')}
                  className="btn-terminal"
                  style={{
                    background: adjustmentType === 'reward' ? 'var(--accent-green-glow)' : 'transparent',
                    borderColor: adjustmentType === 'reward' ? 'var(--accent-green)' : 'var(--border-subtle)',
                    color: adjustmentType === 'reward' ? 'var(--accent-green)' : 'var(--text-secondary)',
                    justifyContent: 'center',
                    fontSize: '12px',
                  }}
                >
                  <Gift size={14} />
                  <span>+ Recompensa</span>
                </button>
                <button
                  type="button"
                  onClick={() => setAdjustmentType('external_purchase')}
                  className="btn-terminal"
                  style={{
                    background: adjustmentType === 'external_purchase' ? 'var(--accent-red-glow)' : 'transparent',
                    borderColor: adjustmentType === 'external_purchase' ? 'var(--accent-red)' : 'var(--border-subtle)',
                    color: adjustmentType === 'external_purchase' ? 'var(--accent-red)' : 'var(--text-secondary)',
                    justifyContent: 'center',
                    fontSize: '12px',
                  }}
                >
                  <ShoppingBag size={14} />
                  <span>- Gasto Externo</span>
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                {adjustmentType === 'external_purchase' ? 'Valor Gasto (Coins):' : 'Valor Recebido (Coins):'}
              </label>
              <input
                type="number"
                step="1"
                min="1"
                className="input-terminal mono"
                value={amount}
                onChange={(e) => setAmount(Math.abs(parseInt(e.target.value, 10) || 0))}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Origem / Motivo (Ex: Squad Battles, Rivals, DME):</label>
              <input
                type="text"
                className="input-terminal"
                placeholder={adjustmentType === 'reward' ? 'Ex: Recompensa Rivals Divisão 4' : 'Ex: Comprei lateral pro time'}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px 14px', borderRadius: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
              <strong>Nota contábil:</strong> Ajustes externos alteram o saldo de caixa ({adjustmentType === 'external_purchase' ? '-' : '+'}), mas <em>não poluem o lucro das operações de trading</em> nem distorcem o win rate.
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn-terminal">
              Cancelar
            </button>
            <button type="submit" disabled={loading} className="btn-terminal primary">
              {loading ? 'Salvando...' : 'Salvar Ajuste'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
