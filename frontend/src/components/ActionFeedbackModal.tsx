'use client';

import React, { useState, useEffect } from 'react';
import { ActionRecommendation, ActionFeedbackPayload, PurchaseItem } from '@/types';
import { api } from '@/lib/api';
import { X, CheckCircle2, XCircle, Plus, Trash2 } from 'lucide-react';

interface ActionFeedbackModalProps {
  isOpen: boolean;
  action: ActionRecommendation | null;
  mode: 'BOUGHT' | 'MISSED';
  onClose: () => void;
  onSuccess: () => void;
}

export const ActionFeedbackModal: React.FC<ActionFeedbackModalProps> = ({
  isOpen,
  action,
  mode,
  onClose,
  onSuccess,
}) => {
  // Estado para COMPREI: lista de preços individuais por carta
  const [purchases, setPurchases] = useState<PurchaseItem[]>([]);
  
  // Estado para NÃO CONSEGUI
  const [missedReason, setMissedReason] = useState<string>('price_rose');
  const [notes, setNotes] = useState<string>('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inicializa a lista de compras com a quantidade recomendada e o max_buy_price
  useEffect(() => {
    if (action && mode === 'BOUGHT') {
      const initialQty = Math.max(1, action.recommended_quantity || 1);
      const initialList: PurchaseItem[] = [];
      for (let i = 0; i < initialQty; i++) {
        initialList.push({ buy_price: action.max_buy_price });
      }
      setPurchases(initialList);
    }
  }, [action, mode]);

  if (!isOpen || !action) return null;

  const handleAddCard = () => {
    setPurchases((prev) => [...prev, { buy_price: action.max_buy_price }]);
  };

  const handleRemoveCard = (index: number) => {
    if (purchases.length <= 1) return;
    setPurchases((prev) => prev.filter((_, i) => i !== index));
  };

  const handlePriceChange = (index: number, value: number) => {
    setPurchases((prev) => {
      const next = [...prev];
      next[index] = { buy_price: value };
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload: ActionFeedbackPayload = {
        recommendation_id: action.id,
        action_result: mode,
        purchases: mode === 'BOUGHT' ? purchases : [],
        missed_reason: mode === 'MISSED' ? missedReason : undefined,
        notes: notes.trim() || undefined,
      };

      await api.sendActionFeedback(payload);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Erro ao registrar feedback');
    } finally {
      setLoading(false);
    }
  };

  const totalCost = purchases.reduce((acc, p) => acc + (p.buy_price || 0), 0);

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '520px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {mode === 'BOUGHT' ? (
              <CheckCircle2 size={20} style={{ color: 'var(--accent-green)' }} />
            ) : (
              <XCircle size={20} style={{ color: 'var(--accent-red)' }} />
            )}
            <h3 style={{ fontSize: '16px', fontWeight: '800' }}>
              {mode === 'BOUGHT' ? 'Registrar Compras Efetivas' : 'Informar Não Execução'}
            </h3>
          </div>
          <button onClick={onClose} className="btn-terminal" style={{ padding: '4px' }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ background: 'var(--accent-red-glow)', color: 'var(--accent-red)', padding: '10px 14px', borderRadius: '8px', fontSize: '13px' }}>
                {error}
              </div>
            )}

            <div style={{ background: 'var(--bg-surface-elevated)', padding: '12px 16px', borderRadius: '10px', fontSize: '13px' }}>
              <div style={{ fontWeight: '700', color: '#fff' }}>{action.player_name} ({action.player_rating})</div>
              <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
                Teto sugerido: {action.max_buy_price.toLocaleString()} coins | Alvo de venda: {action.target_sell_price.toLocaleString()} coins
              </div>
            </div>

            {mode === 'BOUGHT' ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <label className="form-label" style={{ margin: 0 }}>
                    Cartas Compradas ({purchases.length})
                  </label>
                  <button
                    type="button"
                    onClick={handleAddCard}
                    className="btn-terminal"
                    style={{ fontSize: '11px', padding: '4px 10px' }}
                  >
                    <Plus size={13} />
                    <span>+ Adicionar Carta</span>
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '220px', overflowY: 'auto' }}>
                  {purchases.map((p, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', minWidth: '60px' }}>
                        Carta #{idx + 1}
                      </span>
                      <input
                        type="number"
                        step="1"
                        min="1"
                        className="input-terminal mono"
                        value={p.buy_price}
                        onChange={(e) => handlePriceChange(idx, parseInt(e.target.value, 10) || 0)}
                        style={{ flex: 1, padding: '8px 12px' }}
                        required
                      />
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>coins</span>
                      {purchases.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveCard(idx)}
                          className="btn-terminal"
                          style={{ padding: '6px', color: 'var(--accent-red)', border: 'none' }}
                          title="Remover"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Custo Total do Lote:</span>
                  <span className="mono" style={{ fontSize: '16px', fontWeight: '800', color: 'var(--accent-gold)' }}>
                    {totalCost.toLocaleString()} coins
                  </span>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="form-group">
                  <label className="form-label">Motivo principal de não ter comprado:</label>
                  <select
                    className="input-terminal"
                    value={missedReason}
                    onChange={(e) => setMissedReason(e.target.value)}
                  >
                    <option value="price_rose">Preço subiu antes de comprar / snipado por outro</option>
                    <option value="no_cards_found">Nenhuma carta encontrada por até o teto sugerido</option>
                    <option value="lost_bids">Perdi os lances nos leilões disputados</option>
                    <option value="given_up">Desisti / Sem tempo para realizar agora</option>
                    <option value="other">Outro motivo</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Observações (opcional):</label>
                  <input
                    type="text"
                    className="input-terminal"
                    placeholder="Ex: Menor valor no mercado estava 650 coins..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn-terminal">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`btn-terminal ${mode === 'BOUGHT' ? 'primary' : ''}`}
              style={{
                background: mode === 'BOUGHT' ? 'var(--accent-green)' : 'var(--accent-red)',
                color: '#fff',
                fontWeight: '700',
              }}
            >
              {loading ? 'Salvando...' : mode === 'BOUGHT' ? 'Confirmar Compras' : 'Confirmar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
