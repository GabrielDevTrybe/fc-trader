'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { X, RefreshCw, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';

interface BankrollSyncModalProps {
  isOpen: boolean;
  currentTrackedBalance: number;
  isPaper: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const BankrollSyncModal: React.FC<BankrollSyncModalProps> = ({
  isOpen,
  currentTrackedBalance,
  isPaper,
  onClose,
  onSuccess,
}) => {
  const [actualBalanceStr, setActualBalanceStr] = useState<string>('');
  const [reason, setReason] = useState<string>('Sincronização com saldo do jogo');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const actualBalance = parseInt(actualBalanceStr, 10);
  const delta = !isNaN(actualBalance) ? actualBalance - currentTrackedBalance : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (isNaN(actualBalance) || actualBalance < 0) {
      setError('Informe um saldo válido de moedas');
      setLoading(false);
      return;
    }

    try {
      await api.syncBankroll({
        current_actual_balance: actualBalance,
        reason: reason.trim() || undefined,
        is_paper: isPaper,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Erro ao sincronizar saldo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '480px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <RefreshCw size={18} style={{ color: 'var(--accent-cyan)' }} />
            <h3 style={{ fontSize: '16px', fontWeight: '800' }}>Sincronização / Reconciliação de Saldo</h3>
          </div>
          <button onClick={onClose} className="btn-terminal" style={{ padding: '4px' }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ background: 'var(--accent-red-glow)', color: 'var(--accent-red)', padding: '10px 14px', borderRadius: '8px', fontSize: '13px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <AlertCircle size={15} />
                <span>{error}</span>
              </div>
            )}

            <div style={{ background: 'var(--bg-surface-elevated)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Saldo Atual Rastreado no FC Trader:
              </div>
              <div style={{ fontSize: '20px', fontWeight: '800', color: 'var(--accent-gold)' }}>
                {currentTrackedBalance.toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Meu saldo real no EA FC agora é:</label>
              <input
                className="input-terminal"
                type="number"
                value={actualBalanceStr}
                onChange={(e) => setActualBalanceStr(e.target.value)}
                placeholder="Ex: 5430"
                min="0"
                step="1"
                required
                autoFocus
                style={{ fontSize: '18px', fontWeight: 700, padding: '12px', color: '#fff' }}
              />
            </div>

            {actualBalanceStr && !isNaN(actualBalance) && (
              <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '12px 14px', borderRadius: '8px', marginTop: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Ajuste de Reconciliação:</span>
                  <span className="mono" style={{ fontWeight: 800, color: delta >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontSize: '15px' }}>
                    {delta >= 0 ? `+${delta.toLocaleString()}` : delta.toLocaleString()} coins
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                  <ShieldAlert size={14} style={{ color: 'var(--accent-cyan)', flexShrink: 0, marginTop: '2px' }} />
                  <span>
                    Esta diferença é tratada estritamente como <strong>reconciliação de saldo</strong> e <strong>JAMAIS</strong> será contabilizada como lucro de operações de trading.
                  </span>
                </div>
              </div>
            )}

            <div className="form-group" style={{ marginTop: '16px' }}>
              <label className="form-label">Motivo do Ajuste (Opcional):</label>
              <input
                className="input-terminal"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Ex: Correção de saldo verificado no jogo"
                maxLength={100}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn-terminal">
              Cancelar
            </button>
            <button
              type="submit"
              className="btn-terminal primary"
              disabled={loading || !actualBalanceStr}
              id="btn-confirm-sync"
            >
              {loading ? 'Sincronizando...' : 'Sincronizar Saldo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
