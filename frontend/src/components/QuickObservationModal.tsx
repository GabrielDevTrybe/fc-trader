'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';
import { ObservationBatchItem, OpportunityAnalysis } from '@/types';
import { X, Plus, AlertCircle, CheckCircle2 } from 'lucide-react';

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
  const [activeTab, setActiveTab] = useState<'single' | 'batch' | 'csv'>('single');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<OpportunityAnalysis[] | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Single form state - Inicializa limpo e genérico
  const [player, setPlayer] = useState('');
  const [rating, setRating] = useState('');
  const [price, setPrice] = useState('');
  const [type, setType] = useState<'buy_now' | 'bid'>('bid');
  const [position, setPosition] = useState('');
  const [club, setClub] = useState('');
  const [platform, setPlatform] = useState<'console' | 'pc'>('console');

  // Batch paste state
  const [batchRaw, setBatchRaw] = useState('');

  // CSV paste state
  const [csvRaw, setCsvRaw] = useState('');

  const EXAMPLE_CSV = `player_name,rating,observed_price,observation_type,club,position,platform,source
Vinicius Jr,89,32000,buy_now,Real Madrid,LW,console,USER_MARKET_CHECK
Vinicius Jr,89,31500,bid,Real Madrid,LW,console,USER_MARKET_CHECK
Rodri,89,31000,buy_now,Manchester City,CDM,console,USER_MARKET_CHECK
Saliba,87,14000,buy_now,Arsenal,CB,console,USER_MARKET_CHECK
Saliba,87,13500,bid,Arsenal,CB,console,USER_MARKET_CHECK`;

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    setResults(null);

    try {
      if (activeTab === 'csv') {
        if (!csvRaw.trim()) {
          throw new Error('Cole o conteúdo CSV antes de enviar.');
        }
        const res = await api.recordObservationsCsv(csvRaw.trim());
        setResults(res.analyses);
        onSuccess();
        return;
      }

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
            club: club.trim() || undefined,
            platform: platform,
          },
        ];
      } else {
        if (!batchRaw.trim()) {
          throw new Error('Cole o JSON com o lote de observações');
        }
        try {
          items = JSON.parse(batchRaw);
          if (!Array.isArray(items)) {
            throw new Error('O JSON deve ser um array de observações');
          }
        } catch (err: any) {
          throw new Error('Formato JSON inválido: ' + err.message);
        }
      }

      const res = await api.recordObservations(items);
      setResults(res.analyses);
      onSuccess();
    } catch (err: any) {
      setErrorMessage(err.message || 'Erro ao processar observações');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '620px' }}>
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
            INDIVIDUAL
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('csv')}
            style={{
              flex: 1,
              padding: '10px',
              background: activeTab === 'csv' ? 'var(--bg-surface)' : 'transparent',
              color: activeTab === 'csv' ? 'var(--text-primary)' : 'var(--text-muted)',
              border: 'none',
              fontWeight: 600,
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            LOTE CSV
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
            LOTE JSON
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
                  <div className="form-group" style={{ flex: 2 }}>
                    <label className="form-label">Jogador</label>
                    <input
                      className="input-terminal"
                      value={player}
                      onChange={(e) => setPlayer(e.target.value)}
                      placeholder="Ex: Vinicius Jr, Mbappé..."
                      required
                    />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label">Rating</label>
                    <input
                      className="input-terminal"
                      type="number"
                      value={rating}
                      onChange={(e) => setRating(e.target.value)}
                      placeholder="Ex: 85"
                      min="40"
                      max="99"
                      required
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Clube / Time (Opcional)</label>
                    <input
                      className="input-terminal"
                      value={club}
                      onChange={(e) => setClub(e.target.value)}
                      placeholder="Ex: Real Madrid, Benfica, etc."
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Posição (Opcional)</label>
                    <input
                      className="input-terminal"
                      value={position}
                      onChange={(e) => setPosition(e.target.value)}
                      placeholder="Ex: CDM, ST, RW"
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
                      placeholder="Ex: 1200"
                      min="100"
                      step="1"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Tipo</label>
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
                  <div className="form-group">
                    <label className="form-label">Plataforma</label>
                    <select
                      className="input-terminal"
                      value={platform}
                      onChange={(e) => setPlatform(e.target.value as any)}
                    >
                      <option value="console">Console</option>
                      <option value="pc">PC</option>
                    </select>
                  </div>
                </div>
              </>
            ) : activeTab === 'csv' ? (
              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label className="form-label" style={{ marginBottom: 0 }}>Importar Lote CSV</label>
                  <button
                    type="button"
                    onClick={() => setCsvRaw(EXAMPLE_CSV)}
                    style={{
                      background: 'none',
                      border: '1px dashed var(--border-subtle)',
                      color: 'var(--accent-primary)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    Carregar Exemplo
                  </button>
                </div>
                <textarea
                  className="input-terminal"
                  style={{ minHeight: '160px', resize: 'vertical', fontFamily: 'var(--font-mono, monospace)', fontSize: '11px' }}
                  value={csvRaw}
                  onChange={(e) => setCsvRaw(e.target.value)}
                  placeholder="player_name,rating,observed_price,observation_type,club,position,platform,source&#10;Vinicius Jr,89,32000,buy_now,Real Madrid,LW,console,USER_MARKET_CHECK"
                />
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Colunas suportadas: <code>player_name, rating, observed_price, observation_type, club, position, platform, source</code>
                </div>
              </div>
            ) : (
              <div className="form-group">
                <label className="form-label">Array JSON de Observações</label>
                <textarea
                  className="input-terminal"
                  style={{ minHeight: '140px', resize: 'vertical' }}
                  value={batchRaw}
                  onChange={(e) => setBatchRaw(e.target.value)}
                  placeholder='[&#10;  { "player": "Nome", "rating": 84, "price": 1200, "type": "bid", "club": "Clube", "platform": "console" }&#10;]'
                />
              </div>
            )}

            {results && results.length > 0 && (
              <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  RESULTADO DA ANÁLISE INSTANTÂNEA ({results.length}):
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto' }}>
                  {results.map((r, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'var(--bg-surface-elevated)',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <strong>{r.player_name} ({r.rating})</strong> {r.club ? `• ${r.club}` : ''}
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Obs: {r.observed_price.toLocaleString()} | Justo: {r.market_price ? `${r.market_price.toLocaleString()} coins` : 'Calculando...'}
                        </div>
                      </div>
                      <span className={`badge ${r.recommendation === 'BUY' ? 'green' : r.recommendation === 'WATCH' ? 'gold' : 'gray'}`}>
                        {r.recommendation}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn-terminal">
              Fechar
            </button>
            <button
              type="submit"
              className="btn-terminal primary"
              disabled={loading}
            >
              {loading ? 'Processando...' : 'Registrar Observações'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
