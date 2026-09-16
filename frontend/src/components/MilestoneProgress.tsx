'use client';

import React from 'react';
import { BankrollMilestone } from '@/types';
import { CheckCircle2, CircleDot } from 'lucide-react';

interface MilestoneProgressProps {
  milestones: BankrollMilestone[];
  currentBalance: number;
}

export const MilestoneProgress: React.FC<MilestoneProgressProps> = ({
  milestones,
  currentBalance,
}) => {
  return (
    <div className="milestone-container">
      <div className="milestone-header">
        <span className="milestone-title">Progressão de Metas de Banca</span>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          Atual: {currentBalance.toLocaleString('pt-BR')} coins
        </span>
      </div>

      <div className="milestone-steps">
        {/* Ponto inicial de 5k */}
        <div className="milestone-step achieved">
          <div className="step-label" style={{ color: 'var(--accent-green)' }}>5k</div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Start</div>
        </div>

        {milestones.map((m) => {
          const isCurrent = !m.achieved && currentBalance < m.target;
          return (
            <div
              key={m.target}
              className={`milestone-step ${m.achieved ? 'achieved' : isCurrent ? 'current' : ''}`}
            >
              <div className="step-label">
                {m.label}
              </div>
              <div className="step-progress-bar">
                <div
                  className="step-progress-fill"
                  style={{
                    width: `${m.progress_percentage}%`,
                    background: m.achieved ? 'var(--accent-green)' : 'var(--accent-gold)',
                  }}
                />
              </div>
              <div style={{ fontSize: '10px', marginTop: '4px', color: 'var(--text-muted)' }}>
                {m.achieved ? (
                  <span style={{ color: 'var(--accent-green)' }}>Alcançado</span>
                ) : (
                  <span>{m.progress_percentage.toFixed(0)}%</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
