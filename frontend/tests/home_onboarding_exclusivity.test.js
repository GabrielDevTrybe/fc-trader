const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const pageFilePath = path.resolve(__dirname, '..', 'src', 'app', 'page.tsx');
const actionHeroFilePath = path.resolve(__dirname, '..', 'src', 'components', 'ActionHeroCard.tsx');

test('Home structural exclusivity: ActionHeroCard does NOT duplicate RealBankrollOnboardingCard', () => {
  const actionHeroSource = fs.readFileSync(actionHeroFilePath, 'utf-8');
  assert.strictEqual(
    actionHeroSource.includes('RealBankrollOnboardingCard'),
    false,
    'ActionHeroCard should NOT import or render RealBankrollOnboardingCard to maintain single responsibility'
  );
  assert.strictEqual(
    actionHeroSource.includes('isConfigured = true'),
    false,
    'ActionHeroCard should not have permissive isConfigured = true default parameter'
  );
});

test('Home structural exclusivity: page.tsx defines deterministic isRealBankrollUnconfigured rule', () => {
  const pageSource = fs.readFileSync(pageFilePath, 'utf-8');
  
  // Rule verification
  assert.ok(
    pageSource.includes('isRealBankrollUnconfigured = !isPaperMode && capitalSummary?.is_configured !== true'),
    'page.tsx must use strict !== true check so unconfigured state triggers when null/undefined/false'
  );
});

test('Home structural exclusivity: unconfigured real bankroll renders strictly Header and RealBankrollOnboardingCard', () => {
  const pageSource = fs.readFileSync(pageFilePath, 'utf-8');

  // Verify early return for unconfigured state
  const startIndex = pageSource.indexOf('if (isRealBankrollUnconfigured)');
  assert.ok(startIndex !== -1, 'page.tsx must have an explicit if (isRealBankrollUnconfigured) block');

  const endIndex = pageSource.indexOf('// 3. ESTADO OPERACIONAL NORMAL', startIndex);
  assert.ok(endIndex !== -1, 'page.tsx must separate unconfigured state from normal operational state');

  const unconfiguredBlock = pageSource.slice(startIndex, endIndex);

  // Must render Header and RealBankrollOnboardingCard
  assert.ok(unconfiguredBlock.includes('<Header'), 'Unconfigured state must include Header');
  assert.ok(unconfiguredBlock.includes('<RealBankrollOnboardingCard'), 'Unconfigured state must include RealBankrollOnboardingCard');

  // Must NOT render operational cockpit cards
  assert.strictEqual(
    unconfiguredBlock.includes('<ActionHeroCard'),
    false,
    'Unconfigured state must NOT render ActionHeroCard'
  );
  assert.strictEqual(
    unconfiguredBlock.includes('<GoalProgressCard'),
    false,
    'Unconfigured state must NOT render GoalProgressCard'
  );
  assert.strictEqual(
    unconfiguredBlock.includes('<BankrollCapitalCard'),
    false,
    'Unconfigured state must NOT render BankrollCapitalCard'
  );
  assert.strictEqual(
    unconfiguredBlock.includes('<OpenPositionsList'),
    false,
    'Unconfigured state must NOT render OpenPositionsList'
  );
});

test('Home state logic: boolean evaluation for paper vs real bankroll configuration states', () => {
  const evaluateIsUnconfigured = (isPaperMode, capitalSummary) => {
    return !isPaperMode && capitalSummary?.is_configured !== true;
  };

  // Case 1: Paper trading mode (always false for real onboarding block)
  assert.strictEqual(evaluateIsUnconfigured(true, null), false);
  assert.strictEqual(evaluateIsUnconfigured(true, { is_configured: true }), false);
  assert.strictEqual(evaluateIsUnconfigured(true, { is_configured: false }), false);

  // Case 2: Real bankroll loading / initial null state -> MUST be unconfigured
  assert.strictEqual(evaluateIsUnconfigured(false, null), true);

  // Case 3: Real bankroll explicit unconfigured -> MUST be unconfigured
  assert.strictEqual(evaluateIsUnconfigured(false, { is_configured: false }), true);

  // Case 4: Real bankroll missing is_configured field -> MUST be unconfigured
  assert.strictEqual(evaluateIsUnconfigured(false, {}), true);

  // Case 5: Real bankroll configured successfully -> ONLY THEN unconfigured is false
  assert.strictEqual(evaluateIsUnconfigured(false, { is_configured: true }), false);
});

test('RealBankrollOnboardingCard inputs accept positive integers with step=1 and validate target > cash', () => {
  const cardFilePath = path.resolve(__dirname, '..', 'src', 'components', 'RealBankrollOnboardingCard.tsx');
  const cardSource = fs.readFileSync(cardFilePath, 'utf-8');

  // Verify inputs use step="1"
  const stepOccurrences = (cardSource.match(/step="1"/g) || []).length;
  assert.ok(stepOccurrences >= 2, 'Both cash and target inputs must specify step="1"');

  // Verify inputs use min="1" to accept any positive integer
  const minOccurrences = (cardSource.match(/min="1"/g) || []).length;
  assert.ok(minOccurrences >= 2, 'Both cash and target inputs must specify min="1"');

  // Verify business rule validation (target strictly greater than cash)
  assert.ok(
    cardSource.includes('target <= cash'),
    'Component must enforce business validation target_balance > starting_balance'
  );
});

