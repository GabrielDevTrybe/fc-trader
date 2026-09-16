'use client';

import React from 'react';
import { Activity, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  apiConnected: boolean;
  isPaperMode: boolean;
  onTogglePaperMode: (paper: boolean) => void;
  onOpenQuickEntry: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  apiConnected,
  isPaperMode,
  onTogglePaperMode,
  onOpenQuickEntry,
}) => {
  return (
    <header className="terminal-header">
      <div className="brand-area">
        <div className="brand-badge">FC 27</div>
        <div className="brand-title">
          <span>FC TRADER</span>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 'normal' }}>
            TERMINAL v1.0
          </span>
        </div>
      </div>

      <div className="header-status">
        <div className="status-indicator">
          <div className={`status-dot ${apiConnected ? '' : 'warning'}`} />
          <span>{apiConnected ? 'API ONLINE' : 'API OFFLINE / CONECTANDO'}</span>
        </div>

        <div style={{ display: 'flex', background: 'var(--bg-surface-elevated)', borderRadius: '8px', padding: '3px' }}>
          <button
            onClick={() => onTogglePaperMode(false)}
            className="btn-terminal"
            style={{
              padding: '6px 12px',
              fontSize: '11px',
              background: !isPaperMode ? 'var(--border-active)' : 'transparent',
              border: 'none',
            }}
          >
            REAL BANKROLL
          </button>
          <button
            onClick={() => onTogglePaperMode(true)}
            className="btn-terminal"
            style={{
              padding: '6px 12px',
              fontSize: '11px',
              background: isPaperMode ? 'var(--accent-gold)' : 'transparent',
              color: isPaperMode ? '#000' : 'var(--text-secondary)',
              border: 'none',
              fontWeight: '700',
            }}
          >
            PAPER TRADING
          </button>
        </div>

        <button onClick={onOpenQuickEntry} className="btn-terminal primary" id="btn-quick-entry">
          <Activity size={15} />
          <span>+ ENTRADA RÁPIDA</span>
        </button>
      </div>
    </header>
  );
};
