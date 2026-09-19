import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const projectRoot = path.resolve(process.cwd());
const modalPath = path.join(projectRoot, 'src', 'components', 'QuickObservationModal.tsx');
const heroPath = path.join(projectRoot, 'src', 'components', 'ActionHeroCard.tsx');
const apiPath = path.join(projectRoot, 'src', 'lib', 'api.ts');
const typesPath = path.join(projectRoot, 'src', 'types', 'index.ts');

test('Phase 3A: QuickObservationModal includes CSV batch tab and loader', () => {
  const content = fs.readFileSync(modalPath, 'utf8');
  assert.ok(content.includes("'single' | 'batch' | 'csv'"), 'Modal state includes csv tab');
  assert.ok(content.includes('LOTE CSV'), 'Modal renders LOTE CSV button');
  assert.ok(content.includes('recordObservationsCsv'), 'Modal calls api.recordObservationsCsv');
  assert.ok(content.includes('Carregar Exemplo'), 'Modal provides Carregar Exemplo button');
  assert.ok(content.includes('USER_MARKET_CHECK'), 'Example includes USER_MARKET_CHECK');
});

test('Phase 3A: ActionHeroCard renders strategy type, data age, and reason code', () => {
  const content = fs.readFileSync(heroPath, 'utf8');
  assert.ok(content.includes('strategy_type'), 'Hero card supports strategy_type');
  assert.ok(content.includes('market_data_age_seconds'), 'Hero card supports market_data_age_seconds');
  assert.ok(content.includes('no_action_reason_code'), 'Hero card renders typed reason code');
  assert.ok(content.includes('URGÊNCIA'), 'Hero card shows urgency');
});

test('Phase 3A: ActionHeroCard renders dynamic no-action title, message, and suggestion', () => {
  const content = fs.readFileSync(heroPath, 'utf8');
  assert.ok(content.includes('actionResponse?.title'), 'Hero card renders dynamic title');
  assert.ok(content.includes('actionResponse?.message'), 'Hero card renders dynamic message');
  assert.ok(content.includes('actionResponse?.suggestion'), 'Hero card renders dynamic suggestion');
  assert.ok(content.includes('actionResponse?.no_action_reason_code'), 'Hero card renders dynamic status/reason code');
});

test('Phase 3A: API client includes recordObservationsCsv and getCardSnapshots', () => {
  const content = fs.readFileSync(apiPath, 'utf8');
  assert.ok(content.includes('recordObservationsCsv'), 'API client exports recordObservationsCsv');
  assert.ok(content.includes('/observations/batch/csv'), 'Endpoint points to batch CSV');
  assert.ok(content.includes('getCardSnapshots'), 'API client exports getCardSnapshots');
  assert.ok(content.includes('/observations/snapshots/'), 'Endpoint points to snapshots');
});

test('Phase 3A: Types declare MarketSnapshot and Phase 3A properties', () => {
  const content = fs.readFileSync(typesPath, 'utf8');
  assert.ok(content.includes('export interface MarketSnapshot'), 'Declares MarketSnapshot');
  assert.ok(content.includes('strategy_type?: StrategyType'), 'ActionRecommendation includes strategy_type');
  assert.ok(content.includes('market_data_age_seconds?: number'), 'ActionRecommendation includes market_data_age_seconds');
  assert.ok(content.includes('no_action_reason_code?: string'), 'CurrentActionResponse includes no_action_reason_code');
  assert.ok(content.includes('confidence_score'), 'MarketSnapshot includes confidence_score');
});

test('Phase 3A Regressions: api.verifyMarket and anti-cache headers in fetchJson', () => {
  const content = fs.readFileSync(apiPath, 'utf8');
  assert.ok(content.includes('verifyMarket'), 'API client exports verifyMarket');
  assert.ok(content.includes('/actions/verify'), 'API client points to POST /actions/verify');
  assert.ok(content.includes("cache: 'no-store'"), 'fetchJson forces cache: no-store');
  assert.ok(content.includes("'Cache-Control': 'no-cache, no-store, must-revalidate'"), 'fetchJson injects anti-cache headers');
});

test('Phase 3A Regressions: Home page implements race condition guards and explicit verify handler', () => {
  const pagePath = path.join(projectRoot, 'src', 'app', 'page.tsx');
  const content = fs.readFileSync(pagePath, 'utf8');
  assert.ok(content.includes('activeRequestIdRef'), 'page.tsx implements request sequence ID guard');
  assert.ok(content.includes('activeModeRef'), 'page.tsx implements active mode tag guard');
  assert.ok(content.includes('handleVerifyMarket'), 'page.tsx implements explicit verify handler');
  assert.ok(content.includes('isVerifying'), 'page.tsx manages isVerifying state');
  assert.ok(content.includes('lastVerifiedAt'), 'page.tsx tracks lastVerifiedAt timestamp');
  assert.ok(content.includes('Promise.all'), 'page.tsx fetches data concurrently via Promise.all');
});

test('Phase 3A Regressions: ActionHeroCard renders isVerifying spinner and disabled state', () => {
  const content = fs.readFileSync(heroPath, 'utf8');
  assert.ok(content.includes('isVerifying'), 'Hero card supports isVerifying prop');
  assert.ok(content.includes('Verificando...'), 'Hero card renders Verificando text when verifying');
  assert.ok(content.includes('disabled={isVerifying'), 'Hero card disables button while verifying');
});

test('Phase 3A Final (Requirements D & E): Polling removed and explicit re-evaluation on QuickObservationModal', () => {
  const pagePath = path.join(projectRoot, 'src', 'app', 'page.tsx');
  const content = fs.readFileSync(pagePath, 'utf8');
  assert.ok(!content.includes('8000'), '8-second polling timer was completely removed');
  assert.ok(!content.includes('scheduleNext'), 'scheduleNext polling recursion was completely removed');
  assert.ok(content.includes('onSuccess={() => handleVerifyMarket()}'), 'QuickObservationModal triggers explicit verify on success');
});

test('Phase 3A Final (Requirement I): ActionHeroCard displays conservative max_buy metrics as primary', () => {
  const content = fs.readFileSync(heroPath, 'utf8');
  assert.ok(content.includes('profit_at_max_buy'), 'Hero card reads profit_at_max_buy');
  assert.ok(content.includes('roi_at_max_buy'), 'Hero card reads roi_at_max_buy');
  assert.ok(content.includes('Lucro Mínimo Estimado no Teto'), 'Primary metric title is Lucro Mínimo Estimado no Teto');
  assert.ok(content.includes('carta no teto (ROI:'), 'Primary subtext explicitly binds ROI to ceiling');
  assert.ok(content.includes('Na cotação observada de'), 'Secondary line explains observed price scenario');
  assert.ok(!content.toLowerCase().includes('garantid'), 'Does not use the word garantido/garantida');
});

test('Phase 3A Final (Requirement J): WhyExplanationModal uses conservative ceiling metrics and no garantida', () => {
  const whyModalPath = path.join(projectRoot, 'src', 'components', 'WhyExplanationModal.tsx');
  const content = fs.readFileSync(whyModalPath, 'utf8');
  assert.ok(content.includes('Lucro Mínimo Estimado no Teto / Carta'), 'Modal title states Lucro Mínimo Estimado no Teto / Carta');
  assert.ok(!content.includes('Margem Líquida Garantida'), 'Modal does not state Margem Líquida Garantida');
  assert.ok(!content.toLowerCase().includes('garantid'), 'Modal does not use the word garantido/garantida');
});


