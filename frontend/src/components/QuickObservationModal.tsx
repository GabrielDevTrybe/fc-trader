'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { ObservationBatchItem, OpportunityAnalysis } from '@/types';
import { X, Send, CheckCircle2, AlertCircle } from 'lucide-react';

interface QuickObservationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const QuickObservationModal: React.FC<QuickObservationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'single' | 'batch'>('single');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<OpportunityAnalysis[] | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Single form state
  const [player, setPlayer] = useState('Palhinha');
  const [rating, setRating] = useState('82');
  const [price, setPrice] = useState('600');
  const [type, setType] = useState<'buy_now' | 'bid'>('bid');
  const [position, setPosition] = useState('CDM');

  // Batch paste state
  const [batchRaw, setBatchRaw] = useState(
    JSON.stringify(
      [
        { player: 'Palhinha', rating: 82, price: 1000, type: 'buy_now', position: 'CDM' },
        { player: 'Palhinha', rating: 82, price: 1050, type: 'buy_now', position: 'CDM' },
        { player: 'Palhinha', rating: 82, price: 1050, type: 'buy_now', position: 'CDM' },
        { player: 'Palhinha', rating: 82, price: 600, type: 'bid', position: 'CDM' },
      ],
      null,
      2
    )
  );

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    setResults(null);

    try {
      let items: ObservationBatchItem[] = [];

      if (activeTab === 'single') {
        if (!player.trim() || !rating || !price) {
          throw new Error('Preencha os campos obrigatórios (Jogador, Rating e Preço)');
        }
        items = [
          {
            player: player.trim(),
            rating: parseInt(rating, 10),
            price: parseInt(price, 10),
            type: type,
            position: position.trim() || undefined,
          },
        ];
      } else {
        const parsed = JSON.parse(batchRaw);
        if (!Array.isArray(parsed)) {
          throw new Error('O formato em lote deve ser um array JSON de observações');
        }
        items = parsed;
      }

      const res = await api.recordObservations(items);
      setResults(res.analyses);
      onSuccess();
    } catch (err: any) {
      setErrorMessage(err.message || 'Erro ao registrar observação');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div style={{ fontWeight: 700, fontSize: '15px' }}>ENTRADA RÁPIDA DE OBSERVAÇÕES</div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-surface-elevated)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('single')}
            style={{
              flex: 1,
              padding: '10px',
              background: activeTab === 'single' ? 'var(--bg-surface)' : 'transparent',
              color: activeTab === 'single' ? 'var(--text-primary)' : 'var(--text-muted)',
              border: 'none',
              fontWeight: 600,
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            OBSERVAÇÃO INDIVIDUAL
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('batch')}
            style={{
              flex: 1,
              padding: '10px',
              background: activeTab === 'batch' ? 'var(--bg-surface)' : 'transparent',
              color: activeTab === 'batch' ? 'var(--text-primary)' : 'var(--text-muted)',
              border: 'none',
              fontWeight: 600,
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            LOTE / BATCH JSON
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errorMessage && (
              <div style={{ background: 'var(--accent-red-glow)', border: '1px solid var(--accent-red)', padding: '10px', borderRadius: '6px', fontSize: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <AlertCircle size={15} color="var(--accent-red)" />
                <span>{errorMessage}</span>
              </div>
            )}

            {activeTab === 'single' ? (
              <>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Jogador</label>
                    <input
                      className="input-terminal"
                      value={player}
                      onChange={(e) => setPlayer(e.target.value)}
                      placeholder="Ex: Palhinha"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Rating (Overall)</label>
                    <input
                      className="input-terminal"
                      type="number"
                      value={rating}
                      onChange={(e) => setRating(e.target.value)}
                      min="40"
                      max="99"
                      required
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Preço Observado (Coins)</label>
                    <input
                      className="input-terminal"
                      type="number"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      min="100"
                      step="50"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Tipo de Observação</label>
                    <select
                      className="input-terminal"
                      value={type}
                      onChange={(e) => setType(e.target.value as any)}
                    >
                      <option value="bid">Lance (Bid)</option>
                      <option value="buy_now">Comprar Já (Buy Now)</option>
                      <option value="sale_estimate">Estimativa de Venda</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Posição (Opcional)</label>
                  <input
                    className="input-terminal"
                    value={position}
                    onChange={(e) => setPosition(e.target.value)}
                    placeholder="Ex: CDM, RW, ST"
                  />
                </div>
              </>
            ) : (
              <div className="form-group">
                <label className="form-label">Array JSON de Observações</label>
                <textarea
                  className="input-terminal"
                  style={{ minHeight: '140px', resize: 'vertical' }}
                  value={batchRaw}
                  onChange={(e) => setBatchRaw(e.target.value)}
                  placeholder="[{ player: 'Palhinha', rating: 82, price: 600, type: 'bid' }]"
                />
              </div>
            )}

            {results && results.length > 0 && (
              <div style={{ marginTop: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px' }}>
                  RESULTADO DO PIPELINE:
                </div>
                {results.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      background: 'var(--bg-surface-elevated)',
                      padding: '10px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      marginBottom: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <strong>{r.player_name} ({r.rating})</strong>
                      <span className={`badge ${r.recommendation === 'BUY' ? 'green' : 'gold'}`}>
                        {r.recommendation}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                      {r.reason}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn-terminal">
              Fechar
            </button>
            <button type="submit" disabled={loading} className="btn-terminal primary">
              <Send size={13} />
              <span>{loading ? 'Processando...' : 'Processar Observação'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
