'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
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
  const [isVerifying, setIsVerifying] = useState(false);
  const [lastVerifiedAt, setLastVerifiedAt] = useState<string | null>(null);

  // Guards contra race condition entre alternância REAL <-> PAPER
  const activeRequestIdRef = useRef<number>(0);
  const activeModeRef = useRef<boolean>(true);

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

  // Carregamento concorrente e atômico dos dados
  const loadData = useCallback(async (modeOverride?: boolean) => {
    const targetMode = modeOverride !== undefined ? modeOverride : activeModeRef.current;
    const requestId = ++activeRequestIdRef.current;

    try {
      // Dispara requisições simultaneamente com Promise.all para reduzir latência e evitar cascata
      const [cap, goal, act, tList] = await Promise.all([
        api.getCapitalSummary(targetMode),
        api.getActiveGoal(targetMode).catch(() => null),
        api.getCurrentAction(targetMode).catch(() => null),
        api.getTrades(targetMode, 'open').catch(() => []),
      ]);

      // PROTEÇÃO DE RACE CONDITION (Adjustment 4):
      // Se a modalidade foi alterada ou outra requisição mais nova foi emitida, descarta integralmente a resposta
      if (requestId !== activeRequestIdRef.current || targetMode !== activeModeRef.current) {
        return;
      }

      // ATUALIZAÇÃO ATÔMICA: Atualiza todos os estados dependentes no mesmo ciclo de renderização
      setCapitalSummary(cap);
      setActiveGoal(goal);
      setActionResponse(act);
      setOpenTrades(tList);
      setApiConnected(true);
    } catch (err) {
      console.error('Falha ao carregar dados do Cockpit de Ação:', err);
      if (requestId === activeRequestIdRef.current) {
        setApiConnected(false);
      }
    } finally {
      if (requestId === activeRequestIdRef.current) {
        setLoading(false);
      }
    }
  }, []);

  // Carga inicial sem polling (atualizações acionadas estritamente por eventos explícitos)
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Alternância determinística e atômica REAL <-> PAPER
  const handleTogglePaperMode = (newMode: boolean) => {
    activeModeRef.current = newMode;
    activeRequestIdRef.current++; // Invalida imediatamente qualquer requisição pendente do modo anterior
    setIsPaperMode(newMode);
    setLoading(true);
    setActionResponse(null);
    setCapitalSummary(null);
    setActiveGoal(null);
    setOpenTrades([]);
    loadData(newMode);
  };

  // Reanálise explícita via botão "Verificar" (Adjustment 1, 2, 3 e 5)
  const handleVerifyMarket = async () => {
    setIsVerifying(true);
    try {
      const res = await api.verifyMarket(isPaperMode);
      setActionResponse(res);
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setLastVerifiedAt(nowStr);

      // Re-sincroniza resumo patrimonial de forma segura
      const cap = await api.getCapitalSummary(isPaperMode);
      setCapitalSummary(cap);
    } catch (err) {
      console.error('Erro ao verificar mercado:', err);
    } finally {
      setIsVerifying(false);
    }
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
        <RealBankrollOnboardingCard onSuccess={() => loadData()} />
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
        isVerifying={isVerifying}
        lastVerifiedAt={lastVerifiedAt}
        onBoughtClick={handleOpenBought}
        onMissedClick={handleOpenMissed}
        onWhyClick={() => setIsWhyOpen(true)}
        onRefresh={handleVerifyMarket}
        onOpenQuickEntry={() => setIsQuickEntryOpen(true)}
      />

      {/* 2. PROGRESSÃO DA META ATIVA */}
      <GoalProgressCard
        goal={activeGoal}
        capital={capitalSummary}
        isPaper={isPaperMode}
        onRefresh={() => loadData()}
      />

      {/* 3. BALANÇO PATRIMONIAL & CAIXA (Sem dupla dedução) */}
      <BankrollCapitalCard
        capital={capitalSummary}
        loading={loading}
        isPaper={isPaperMode}
        onRefresh={() => loadData()}
      />

      {/* 4. POSIÇÕES ABERTAS (Cartas compradas aguardando venda) */}
      <OpenPositionsList
        trades={openTrades}
        loading={loading}
        onRefresh={() => loadData()}
      />

      {/* Modais de Interação Humana */}
      <ActionFeedbackModal
        isOpen={isFeedbackOpen}
        action={actionResponse?.action || null}
        mode={feedbackMode}
        onClose={() => setIsFeedbackOpen(false)}
        onSuccess={() => loadData()}
      />

      <WhyExplanationModal
        isOpen={isWhyOpen}
        action={actionResponse?.action || null}
        onClose={() => setIsWhyOpen(false)}
      />

      <QuickObservationModal
        isOpen={isQuickEntryOpen}
        onClose={() => setIsQuickEntryOpen(false)}
        onSuccess={() => handleVerifyMarket()}
      />
    </main>
  );
}

