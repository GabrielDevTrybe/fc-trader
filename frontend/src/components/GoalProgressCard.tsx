'use client';

import React, { useState } from 'react';
import { TradingGoal, BankrollCapitalSummary } from '@/types';
import { api } from '@/lib/api';
import { Target, Trophy, CheckCircle, PlusCircle, X, Check, Award } from 'lucide-react';

interface GoalProgressCardProps {
  goal: TradingGoal | null;
  capital: BankrollCapitalSummary | null;
  isPaper: boolean;
  onRefresh: () => void;
}

export const GoalProgressCard: React.FC<GoalProgressCardProps> = ({
  goal,
  capital,
  isPaper,
  onRefresh,
}) => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [targetBalance, setTargetBalance] = useState<number>(10000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.createGoal({
        target_balance: targetBalance,
        starting_balance: capital?.total_equity,
        is_paper: isPaper,
      });
      setIsCreateModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Erro ao criar meta');
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteGoal = async () => {
    if (!goal) return;
    if (!confirm('Deseja realmente marcar esta meta como CONCLUÍDA?')) return;
    setLoading(true);
    try {
      await api.completeGoal(goal.id);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Erro ao concluir meta');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseGoal = async () => {
    if (!goal) return;
    if (!confirm('Deseja realmente encerrar este ciclo sem concluir?')) return;
    setLoading(true);
    try {
      await api.closeGoal(goal.id);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Erro ao encerrar meta');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="goal-card" id="goal-progress-card">
      <div className="goal-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Target size={20} style={{ color: 'var(--accent-gold)' }} />
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: '800' }}>
              {goal ? `Meta Ativa: ${goal.target_balance.toLocaleString()} coins` : 'Ciclo de Metas'}
            </h3>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {isPaper ? 'Paper Trading Cycle' : 'Ciclo com Banca Real'}
            </div>
          </div>
        </div>

        {goal ? (
          <div style={{ display: 'flex', gap: '8px' }}>
            {goal.progress_percentage >= 100 && (
              <button
                onClick={handleCompleteGoal}
                className="btn-terminal"
                style={{ background: 'var(--accent-green)', color: '#fff', fontWeight: '700' }}
              >
                <Trophy size={14} />
                <span>Concluir Meta</span>
              </button>
            )}
            <button onClick={handleCloseGoal} className="btn-terminal" style={{ fontSize: '11px' }}>
              Encerrar Ciclo
            </button>
          </div>
        ) : (
          <button
            onClick={() => {
              setTargetBalance((capital?.total_equity || 5000) * 2);
              setIsCreateModalOpen(true);
            }}
            className="btn-terminal primary"
            id="btn-new-goal"
          >
            <PlusCircle size={14} />
            <span>Iniciar Nova Meta</span>
          </button>
        )}
      </div>

      {goal ? (
        <div>
          <div className="goal-progress-bar-container">
            <div
              className="goal-progress-bar-fill"
              style={{ width: `${Math.min(100, Math.max(0, goal.progress_percentage))}%` }}
            />
          </div>

          <div className="goal-stats-row">
            <div>
              <span>Início: </span>
              <strong>{goal.starting_balance.toLocaleString()}</strong> coins
            </div>
            <div>
              <span style={{ color: 'var(--accent-gold)' }}>Progresso: </span>
              <strong>{goal.progress_percentage.toFixed(1)}%</strong>
            </div>
            <div>
              <span>Alvo: </span>
              <strong>{goal.target_balance.toLocaleString()}</strong> coins
            </div>
          </div>

          <div style={{ display: 'flex', gap: '20px', marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', fontSize: '12px', color: 'var(--text-muted)' }}>
            <div>
              Lucro no ciclo: <strong style={{ color: 'var(--accent-green)' }}>+{goal.profit_in_goal.toLocaleString()} coins</strong>
            </div>
            <div>
              Trades no ciclo: <strong style={{ color: '#fff' }}>{goal.trades_count}</strong>
            </div>
            {goal.win_rate !== null && (
              <div>
                Win Rate: <strong style={{ color: 'var(--accent-cyan)' }}>{goal.win_rate.toFixed(1)}%</strong>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div style={{ padding: '16px 0', color: 'var(--text-secondary)', fontSize: '13px' }}>
          Nenhuma meta ativa no momento para esta modalidade. Defina uma meta inicial (ex: 5.000 → 10.000 coins) para guiar as recomendações do StrategyEngine.
        </div>
      )}

      {/* Modal Criar Nova Meta */}
      {isCreateModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '16px', fontWeight: '800' }}>Iniciar Ciclo de Meta</h3>
              <button onClick={() => setIsCreateModalOpen(false)} className="btn-terminal" style={{ padding: '4px' }}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateGoal}>
              <div className="modal-body">
                {error && (
                  <div style={{ background: 'var(--accent-red-glow)', color: 'var(--accent-red)', padding: '10px 14px', borderRadius: '8px', fontSize: '13px' }}>
                    {error}
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">Saldo Inicial da Banca:</label>
                  <input
                    type="text"
                    className="input-terminal mono"
                    value={`${(capital?.total_equity || 0).toLocaleString()} coins`}
                    disabled
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Capturado automaticamente do seu patrimônio atual ({isPaper ? 'Paper Trading' : 'Banca Real'})
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label">Meta de Coins a Atingir:</label>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    className="input-terminal mono"
                    value={targetBalance}
                    onChange={(e) => setTargetBalance(parseInt(e.target.value, 10) || 0)}
                    required
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Ex: 10.000 coins, 20.000 coins, 50.000 coins
                  </span>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setIsCreateModalOpen(false)} className="btn-terminal">
                  Cancelar
                </button>
                <button type="submit" disabled={loading} className="btn-terminal primary">
                  {loading ? 'Criando...' : 'Iniciar Ciclo'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
