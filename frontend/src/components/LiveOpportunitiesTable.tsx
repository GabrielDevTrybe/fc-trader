'use client';

import React from 'react';
import { MarketOpportunity } from '@/types';
import { PlayCircle, ShieldCheck, Flame } from 'lucide-react';

interface LiveOpportunitiesTableProps {
  opportunities: MarketOpportunity[];
  loading: boolean;
  onOpenTrade: (opp: MarketOpportunity) => void;
}

export const LiveOpportunitiesTable: React.FC<LiveOpportunitiesTableProps> = ({
  opportunities,
  loading,
  onOpenTrade,
}) => {
  return (
    <div className="table-card">
      <div className="table-header-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Flame size={16} color="var(--accent-gold)" />
          <span style={{ fontWeight: 800, letterSpacing: '0.5px' }}>LIVE OPPORTUNITIES</span>
          <span className="badge gold">{opportunities.length} ATIVAS</span>
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Ordenado por Opportunity Score determinístico
        </span>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>PLAYER</th>
              <th>RATING</th>
              <th>MARKET</th>
              <th>OBSERVED</th>
              <th>MAX BUY</th>
              <th>TARGET SELL</th>
              <th>EST. PROFIT</th>
              <th>ROI</th>
              <th>LIQUIDITY</th>
              <th>CONFIDENCE</th>
              <th>SCORE</th>
              <th>ACTION</th>
              <th>SIMULAR</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={13} className="empty-state">
                  Carregando oportunidades de mercado...
                </td>
              </tr>
            ) : opportunities.length === 0 ? (
              <tr>
                <td colSpan={13} className="empty-state">
                  <div style={{ fontSize: '14px', marginBottom: '6px' }}>Nenhuma oportunidade viva detectada.</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Insira observações de mercado através do botão <strong>+ ENTRADA RÁPIDA</strong> acima.
                    Se não houver observações suficientes (&lt; 3), o sistema sinalizará <em>insufficient data</em>.
                  </div>
                </td>
              </tr>
            ) : (
              opportunities.map((opp) => {
                const profitFormatted = `+${opp.estimated_profit.toLocaleString('pt-BR')}`;
                const roiFormatted = `${(opp.roi * 100).toFixed(1)}%`;
                const confColor =
                  opp.confidence === 'HIGH' ? 'green' : opp.confidence === 'MEDIUM' ? 'cyan' : 'gray';

                return (
                  <tr key={opp.id}>
                    <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                      <div>{opp.card?.player_name || opp.player?.name || 'Jogador'}</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 400 }}>
                        {opp.card?.rarity || 'Gold'} {opp.card?.position || opp.player?.position ? `• ${opp.card?.position || opp.player?.position}` : ''} {opp.card?.club ? `• ${opp.card.club}` : ''}
                      </div>
                    </td>
                    <td>
                      <span className="badge cyan mono">{opp.card?.rating || opp.player?.rating || '--'}</span>
                    </td>
                    <td className="mono">{opp.market_price.toLocaleString('pt-BR')}</td>
                    <td className="mono" style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>
                      {opp.observed_price.toLocaleString('pt-BR')}
                    </td>
                    <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                      &lt;= {opp.max_buy_price.toLocaleString('pt-BR')}
                    </td>
                    <td className="mono" style={{ color: 'var(--accent-cyan)' }}>
                      {opp.target_sell_price.toLocaleString('pt-BR')}
                    </td>
                    <td className="mono" style={{ color: 'var(--accent-green)', fontWeight: 700 }}>
                      {profitFormatted}
                    </td>
                    <td className="mono" style={{ color: 'var(--accent-green)' }}>
                      {roiFormatted}
                    </td>
                    <td className="mono">
                      <span className={`badge ${opp.liquidity_score >= 70 ? 'green' : 'gold'}`}>
                        {opp.liquidity_score}/100
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${confColor}`}>{opp.confidence}</span>
                    </td>
                    <td className="mono" style={{ fontWeight: 800, color: 'var(--accent-gold)' }}>
                      {opp.opportunity_score.toFixed(1)}
                    </td>
                    <td>
                      <span className="badge green" style={{ fontSize: '11px' }}>
                        BUY &lt;= {opp.max_buy_price}
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => onOpenTrade(opp)}
                        className="btn-terminal"
                        style={{ padding: '4px 8px', fontSize: '11px', gap: '4px' }}
                        title="Simular compra em Paper Trading"
                      >
                        <PlayCircle size={13} color="var(--accent-gold)" />
                        <span>Paper</span>
                      </button>
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
