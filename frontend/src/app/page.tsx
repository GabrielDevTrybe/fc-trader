'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import {
  CurrentActionResponse,
  TradingGoal,
  BankrollCapitalSummary,
  Trade,
} from '@/types';
import { Header } from '@/components/Header';
import { ActionHeroCard } from '@/components/ActionHeroCard';
import { RealBankrollOnboardingCard } from '@/components/RealBankrollOnboardingCard';
import { GoalProgressCard } from '@/components/GoalProgressCard';
import { BankrollCapitalCard } from '@/components/BankrollCapitalCard';
import { OpenPositionsList } from '@/components/OpenPositionsList';
import { ActionFeedbackModal } from '@/components/ActionFeedbackModal';
import { WhyExplanationModal } from '@/components/WhyExplanationModal';
import { QuickObservationModal } from '@/components/QuickObservationModal';

export default function ActionFirstHomePage() {
  const [apiConnected, setApiConnected] = useState(false);
  const [isPaperMode, setIsPaperMode] = useState(true);
  const [loading, setLoading] = useState(true);

  // Phase 2 Data States
  const [actionResponse, setActionResponse] = useState<CurrentActionResponse | null>(null);
  const [activeGoal, setActiveGoal] = useState<TradingGoal | null>(null);
  const [capitalSummary, setCapitalSummary] = useState<BankrollCapitalSummary | null>(null);
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);

  // Modals
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [feedbackMode, setFeedbackMode] = useState<'BOUGHT' | 'MISSED'>('BOUGHT');
  const [isWhyOpen, setIsWhyOpen] = useState(false);
  const [isQuickEntryOpen, setIsQuickEntryOpen] = useState(false);

  const loadData = useCallback(async () => {
    try {
      // 1. Health check
      try {
        await api.getHealth();
        setApiConnected(true);
      } catch {
        setApiConnected(false);
      }

      // 2. Capital Breakdown
      const cap = await api.getCapitalSummary(isPaperMode);
      setCapitalSummary(cap);

      // 3. Active Goal
      try {
        const goal = await api.getActiveGoal(isPaperMode);
        setActiveGoal(goal);
      } catch {
        setActiveGoal(null);
      }

      // 4. Current Action
      const act = await api.getCurrentAction(isPaperMode);
      setActionResponse(act);

      // 5. Open Positions
      const tList = await api.getTrades(isPaperMode, 'open');
      setOpenTrades(tList);
    } catch (err) {
      console.error('Falha ao carregar dados do Cockpit de Ação:', err);
    } finally {
      setLoading(false);
    }
  }, [isPaperMode]);

  // Initial load and polling
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000); // Polling a cada 4 segundos
    return () => clearInterval(interval);
  }, [loadData]);

  const handleTogglePaperMode = (paper: boolean) => {
    setIsPaperMode(paper);
    setLoading(true);
    setActionResponse(null);
    setCapitalSummary(null);
    setActiveGoal(null);
    setOpenTrades([]);
  };

  const handleOpenBought = () => {
    setFeedbackMode('BOUGHT');
    setIsFeedbackOpen(true);
  };

  const handleOpenMissed = () => {
    setFeedbackMode('MISSED');
    setIsFeedbackOpen(true);
  };

  // Verifica se a banca real está desconfigurada
  // No modo REAL, a banca é considerada NÃO configurada a menos que capitalSummary?.is_configured seja explicitamente true.
  const isRealBankrollUnconfigured = !isPaperMode && capitalSummary?.is_configured !== true;

  // 1. ESTADO DE CARREGAMENTO INICIAL
  if (loading && capitalSummary === null) {
    return (
      <main className="container">
        <Header
          apiConnected={apiConnected}
          isPaperMode={isPaperMode}
          onTogglePaperMode={handleTogglePaperMode}
          onOpenQuickEntry={() => setIsQuickEntryOpen(true)}
        />
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '14px', fontWeight: 600 }}>Carregando estado do terminal...</div>
        </div>
      </main>
    );
  }

  // 2. ESTADO ESTRUTURAL EXCLUSIVO: ONBOARDING OBRIGATÓRIO DA BANCA REAL
  // Nenhum componente operacional (ActionHero, Metas, Balanço, Posições) é montado enquanto não configurado.
  if (isRealBankrollUnconfigured) {
    return (
      <main className="container">
        <Header
          apiConnected={apiConnected}
          isPaperMode={isPaperMode}
          onTogglePaperMode={handleTogglePaperMode}
          onOpenQuickEntry={() => setIsQuickEntryOpen(true)}
        />
        <RealBankrollOnboardingCard onSuccess={loadData} />
      </main>
    );
  }

  // 3. ESTADO OPERACIONAL NORMAL (Banca Real Configurada ou Paper Trading)
  return (
    <main className="container">
      <Header
        apiConnected={apiConnected}
        isPaperMode={isPaperMode}
        onTogglePaperMode={handleTogglePaperMode}
        onOpenQuickEntry={() => setIsQuickEntryOpen(true)}
      />

      {/* 1. HERO ACTION CARD: A resposta imediata para "O que fazer agora" */}
      <ActionHeroCard
        actionResponse={actionResponse}
        isPaper={isPaperMode}
        loading={loading}
        onBoughtClick={handleOpenBought}
        onMissedClick={handleOpenMissed}
        onWhyClick={() => setIsWhyOpen(true)}
        onRefresh={loadData}
        onOpenQuickEntry={() => setIsQuickEntryOpen(true)}
      />

      {/* 2. PROGRESSÃO DA META ATIVA */}
      <GoalProgressCard
        goal={activeGoal}
        capital={capitalSummary}
        isPaper={isPaperMode}
        onRefresh={loadData}
      />

      {/* 3. BALANÇO PATRIMONIAL & CAIXA (Sem dupla dedução) */}
      <BankrollCapitalCard
        capital={capitalSummary}
        loading={loading}
        isPaper={isPaperMode}
        onRefresh={loadData}
      />

      {/* 4. POSIÇÕES ABERTAS (Cartas compradas aguardando venda) */}
      <OpenPositionsList
        trades={openTrades}
        loading={loading}
        onRefresh={loadData}
      />

      {/* Modais de Interação Humana */}
      <ActionFeedbackModal
        isOpen={isFeedbackOpen}
        action={actionResponse?.action || null}
        mode={feedbackMode}
        onClose={() => setIsFeedbackOpen(false)}
        onSuccess={loadData}
      />

      <WhyExplanationModal
        isOpen={isWhyOpen}
        action={actionResponse?.action || null}
        onClose={() => setIsWhyOpen(false)}
      />

      <QuickObservationModal
        isOpen={isQuickEntryOpen}
        onClose={() => setIsQuickEntryOpen(false)}
        onSuccess={loadData}
      />
    </main>
  );
}
