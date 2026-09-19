'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, Flame, BarChart3 } from 'lucide-react';

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
  const pathname = usePathname();

  return (
    <header className="terminal-header">
      <div className="brand-area">
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '14px', textDecoration: 'none' }}>
          <div className="brand-badge">FC 27</div>
          <div className="brand-title">
            <span style={{ color: '#fff' }}>FC TRADER</span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'normal' }}>
              ACTION v2.0
            </span>
          </div>
        </Link>

        {/* Navegação entre Cockpit de Ação e Terminal Analítico */}
        <nav style={{ display: 'flex', gap: '6px', marginLeft: '20px' }}>
          <Link
            href="/"
            className="btn-terminal"
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              background: pathname === '/' ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
              borderColor: pathname === '/' ? 'var(--accent-green)' : 'transparent',
              color: pathname === '/' ? 'var(--accent-green)' : 'var(--text-secondary)',
              fontWeight: '700',
              textDecoration: 'none',
            }}
          >
            <Flame size={14} />
            <span>Ação Agora</span>
          </Link>

          <Link
            href="/advanced"
            className="btn-terminal"
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              background: pathname === '/advanced' ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
              borderColor: pathname === '/advanced' ? 'var(--accent-cyan)' : 'transparent',
              color: pathname === '/advanced' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              fontWeight: '700',
              textDecoration: 'none',
            }}
          >
            <BarChart3 size={14} />
            <span>Terminal Analítico</span>
          </Link>
        </nav>
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
