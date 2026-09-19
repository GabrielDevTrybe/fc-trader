'use client';

import React, { useEffect, useState } from 'react';
import { CurrentActionResponse } from '@/types';
import { Flame, Clock, HelpCircle, CheckCircle2, XCircle, RefreshCw, AlertCircle, ShoppingCart, Tag, MapPin, Monitor } from 'lucide-react';

interface ActionHeroCardProps {
  actionResponse: CurrentActionResponse | null;
  isPaper: boolean;
  loading: boolean;
  onBoughtClick: () => void;
  onMissedClick: () => void;
  onWhyClick: () => void;
  onRefresh: () => void;
  onOpenQuickEntry: () => void;
}

export const ActionHeroCard: React.FC<ActionHeroCardProps> = ({
  actionResponse,
  isPaper,
  loading,
  onBoughtClick,
  onMissedClick,
  onWhyClick,
  onRefresh,
  onOpenQuickEntry,
}) => {
  const [timeLeftStr, setTimeLeftStr] = useState<string>('');

  const action = actionResponse?.action;

  // Countdown TTL timer
  useEffect(() => {
    if (!action?.expires_at) {
      setTimeLeftStr('');
      return;
    }

    const updateTimer = () => {
      const now = new Date().getTime();
      const expires = new Date(action.expires_at).getTime();
      const diff = Math.max(0, Math.floor((expires - now) / 1000));

      if (diff <= 0) {
        setTimeLeftStr('EXPIRADO');
      } else {
        const m = Math.floor(diff / 60);
        const s = diff % 60;
        setTimeLeftStr(`${m}m ${s.toString().padStart(2, '0')}s`);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [action?.expires_at]);

  // 2. ESTADO: CARREGANDO
  if (loading && !actionResponse) {
    return (
      <div className="hero-action-card">
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px' }} />
          <p>Analisando oportunidades com melhor margem de risco...</p>
        </div>
      </div>
    );
  }

  // 3. ESTADO: NENHUMA AÇÃO DISPONÍVEL
  if (!action || !actionResponse?.has_action) {
    return (
      <div className="hero-action-card no-action">
        <div className="hero-header-row">
          <div className="hero-title-badge">
            <span className="hero-strategy-pill" style={{ borderColor: 'var(--border-active)', color: 'var(--text-secondary)' }}>
              MERCADO EM OBSERVAÇÃO
            </span>
          </div>
          <button onClick={onRefresh} className="btn-terminal" title="Verificar novas oportunidades">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Verificar</span>
          </button>
        </div>

        <div style={{ padding: '12px 0 20px' }}>
          <h3 style={{ fontSize: '20px', fontWeight: '800', color: '#f8fafc', marginBottom: '8px' }}>
            {actionResponse?.title || 'Nenhuma ação recomendada no momento'}
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', maxWidth: '700px', lineHeight: '1.5' }}>
            {actionResponse?.message ||
              'O FC Trader monitora o mercado e só recomenda operações com lucro comprovado após os 5% de taxa da EA e dentro da sua política de risco.'}
          </p>
          {actionResponse?.suggestion && (
            <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-gold)', fontSize: '13px' }}>
              <AlertCircle size={15} />
              <span>{actionResponse.suggestion}</span>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
          <button onClick={onOpenQuickEntry} className="btn-terminal primary">
            + Inserir Observações do Mercado
          </button>
          <button onClick={onRefresh} className="btn-terminal">
            Atualizar Cotações
          </button>
        </div>
      </div>
    );
  }

  // 4. ESTADO: AÇÃO DISPONÍVEL COM CARD IDENTITY INEQUÍVOCO
  const isExpired = timeLeftStr === 'EXPIRADO';

  return (
    <div className="hero-action-card" id="action-hero-card">
      {/* Cabeçalho */}
      <div className="hero-header-row">
        <div className="hero-title-badge">
          <div className="hero-fire-tag">
            <Flame size={14} />
            <span>Faça Isso Agora</span>
          </div>
          <div className="hero-strategy-pill">
            {action.strategy_name.toUpperCase()}
          </div>
          <span className={`badge ${action.urgency === 'ALTA' ? 'red' : 'gold'}`}>
            URGÊNCIA {action.urgency}
          </span>
        </div>

        <div className="hero-expiry-tag">
          <Clock size={14} />
          <span>Válido por: <strong style={{ color: isExpired ? 'var(--accent-red)' : '#fff' }}>{timeLeftStr}</strong></span>
        </div>
      </div>

      {/* Identificação Inequívoca da Versão da Carta (Card Identity) */}
      <div className="hero-player-box" style={{ alignItems: 'flex-start' }}>
        <div className="player-rating-badge-large">
          {action.player_rating}
        </div>
        <div className="player-identity-text" style={{ flex: 1 }}>
          <h2 style={{ fontSize: '24px', fontWeight: 800, margin: 0, color: '#fff' }}>
            {action.player_name}
          </h2>

          {/* Especificações da Carta: Versão, Posição, Clube, Liga e Mercado */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '6px', alignItems: 'center' }}>
            <span
              style={{
                background: 'rgba(245, 158, 11, 0.15)',
                color: 'var(--accent-gold)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 700,
              }}
            >
              {action.player_rating} • {action.card_version_name || 'Gold'} • {action.card_position || 'N/A'}
            </span>

            <span
              style={{
                background: 'rgba(56, 189, 248, 0.12)',
                color: 'var(--accent-cyan)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 600,
              }}
            >
              {action.card_club || 'Clube N/A'} • {action.card_league || 'Liga N/A'}
            </span>

            {action.card_platform && action.card_platform !== 'all' && (
              <span
                style={{
                  background: 'rgba(168, 85, 247, 0.15)',
                  color: '#c084fc',
                  border: '1px solid rgba(168, 85, 247, 0.3)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <Monitor size={11} />
                MERCADO: {action.card_platform.toUpperCase()}
              </span>
            )}
          </div>

          <div className="player-meta-tags" style={{ marginTop: '8px' }}>
            <span>Preço Justo: ~{action.snapshot_market_price.toLocaleString()} coins</span>
            <span>•</span>
            <span>Liquidez: {action.snapshot_liquidity_score}/100</span>
            <span>•</span>
            <span>Confiança: {action.snapshot_confidence}</span>
          </div>
        </div>
      </div>

      {/* Instrução Direta e Sem Ruído */}
      <div className="instruction-banner">
        <p className="instruction-text">
          Comprar até <span className="instruction-highlight">{action.recommended_quantity}x cartas</span> por até{' '}
          <span className="instruction-highlight">{action.max_buy_price.toLocaleString()} coins</span> cada.
          <br />
          Vender imediatamente por <span className="instruction-sell">{action.target_sell_price.toLocaleString()} coins</span>.
        </p>
      </div>

      {/* Métricas Financeiras e Expectativas */}
      <div className="hero-metrics-grid">
        <div className="hero-metric-tile">
          <div className="label">Comprar Até (Teto)</div>
          <div className="value" style={{ color: 'var(--accent-gold)' }}>
            {action.max_buy_price.toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="subtext">Nunca pague acima desse valor</div>
        </div>

        <div className="hero-metric-tile">
          <div className="label">Preço Alvo de Venda</div>
          <div className="value" style={{ color: 'var(--accent-green)' }}>
            {action.target_sell_price.toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="subtext">Anuncie assim que arrematar</div>
        </div>

        <div className="hero-metric-tile">
          <div className="label">Lucro Líquido Estimado</div>
          <div className="value" style={{ color: 'var(--accent-green)' }}>
            +{action.estimated_total_profit.toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="subtext">+{action.estimated_profit_per_card.toLocaleString()} / carta (ROI: {(action.estimated_roi * 100).toFixed(1)}%)</div>
        </div>

        <div className="hero-metric-tile">
          <div className="label">Capital Máximo Alocado</div>
          <div className="value" style={{ color: '#fff' }}>
            {action.capital_limit.toLocaleString()} <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>coins</span>
          </div>
          <div className="subtext">{action.recommended_quantity}x cartas dentro do teto de risco</div>
        </div>
      </div>

      {/* Barra de Ações Rápidas de Feedback */}
      <div className="hero-action-buttons">
        <button
          onClick={onBoughtClick}
          className="btn-terminal primary"
          style={{ flex: 2, padding: '12px', fontSize: '14px' }}
          id="btn-action-bought"
        >
          <CheckCircle2 size={16} />
          <span>Comprei</span>
        </button>

        <button
          onClick={onMissedClick}
          className="btn-terminal"
          style={{ flex: 1, padding: '12px', fontSize: '14px' }}
          id="btn-action-missed"
        >
          <XCircle size={16} />
          <span>Não Consegui</span>
        </button>

        <button
          onClick={onWhyClick}
          className="btn-terminal secondary"
          style={{ padding: '12px 14px', fontSize: '13px' }}
          id="btn-action-why"
          title="Ver auditoria matemática e justificativa factual"
        >
          <HelpCircle size={15} />
          <span>Por que isso?</span>
        </button>
      </div>
    </div>
  );
};
