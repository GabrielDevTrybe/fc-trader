'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { Coins, Target, ArrowRight, ShieldCheck, AlertCircle } from 'lucide-react';

interface RealBankrollOnboardingCardProps {
  onSuccess: () => void;
}

export const RealBankrollOnboardingCard: React.FC<RealBankrollOnboardingCardProps> = ({ onSuccess }) => {
  const [cashBalance, setCashBalance] = useState<string>('5000');
  const [targetBalance, setTargetBalance] = useState<string>('10000');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const cash = parseInt(cashBalance, 10);
    const target = parseInt(targetBalance, 10);

    if (isNaN(cash) || cash <= 0) {
      setError('Informe um saldo de coins válido (número inteiro positivo)');
      setLoading(false);
      return;
    }

    if (isNaN(target) || target <= 0) {
      setError('Informe uma meta de coins válida (número inteiro positivo)');
      setLoading(false);
      return;
    }

    if (target <= cash) {
      setError('A sua meta de coins deve ser estritamente maior que o saldo inicial');
      setLoading(false);
      return;
    }

    try {
      await api.onboardBankroll({ cash_balance: cash, target_balance: target });
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Falha ao inicializar a banca real');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="hero-action-card"
      style={{
        border: '1px solid rgba(16, 185, 129, 0.35)',
        background: 'linear-gradient(180deg, rgba(16, 185, 129, 0.08) 0%, rgba(15, 23, 42, 0.95) 100%)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 24px rgba(16, 185, 129, 0.15)',
        padding: '28px 24px',
      }}
      id="real-bankroll-onboarding-card"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(16, 185, 129, 0.2)',
            color: 'var(--accent-green)',
            padding: '4px 10px',
            borderRadius: '999px',
            fontSize: '11px',
            fontWeight: 800,
            letterSpacing: '0.5px',
          }}
        >
          <ShieldCheck size={13} />
          MODO BANCA REAL
        </div>
      </div>

      <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
        Configure sua banca
      </h2>

      <p style={{ color: 'var(--text-secondary)', fontSize: '14px', maxWidth: '640px', lineHeight: '1.5', marginBottom: '24px' }}>
        Para garantir recomendações seguras e 100% calibradas para o seu poder de compra, informe seu saldo real no EA FC.
        Nenhuma recomendação de compra será exibida antes da sua banca ser configurada.
      </p>

      {error && (
        <div
          style={{
            background: 'var(--accent-red-glow)',
            border: '1px solid var(--accent-red)',
            color: 'var(--accent-red)',
            padding: '12px 14px',
            borderRadius: '8px',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '20px',
          }}
        >
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ maxWidth: '520px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
          <div className="form-group">
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Coins size={14} style={{ color: 'var(--accent-gold)' }} />
              <span>Quantas coins você possui atualmente?</span>
            </label>
            <input
              className="input-terminal"
              type="number"
              value={cashBalance}
              onChange={(e) => setCashBalance(e.target.value)}
              placeholder="5000"
              min="1"
              step="1"
              required
              style={{
                fontSize: '16px',
                fontWeight: 700,
                color: 'var(--accent-gold)',
                padding: '12px 14px',
              }}
            />
          </div>

          <div className="form-group">
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Target size={14} style={{ color: 'var(--accent-green)' }} />
              <span>Qual sua meta?</span>
            </label>
            <input
              className="input-terminal"
              type="number"
              value={targetBalance}
              onChange={(e) => setTargetBalance(e.target.value)}
              placeholder="10000"
              min="1"
              step="1"
              required
              style={{
                fontSize: '16px',
                fontWeight: 700,
                color: 'var(--accent-green)',
                padding: '12px 14px',
              }}
            />
          </div>
        </div>

        <button
          type="submit"
          className="btn-terminal primary"
          disabled={loading}
          style={{
            width: '100%',
            padding: '14px',
            fontSize: '15px',
            fontWeight: 800,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '8px',
            letterSpacing: '0.5px',
          }}
          id="btn-start-onboarding"
        >
          <span>{loading ? 'Inicializando...' : 'COMEÇAR'}</span>
          <ArrowRight size={16} />
        </button>
      </form>
    </div>
  );
};
