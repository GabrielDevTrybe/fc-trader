from dataclasses import dataclass


@dataclass(frozen=True)
class OpportunityScoreResult:
    score: float  # Pontuação composta (ex: 84.50)
    roi_component: float
    profit_component: float
    liquidity_component: float
    confidence_component: float
    capital_efficiency_multiplier: float
    recency_multiplier: float
    explanation: str


class OpportunityScoreEngine:
    """Motor determinístico para cálculo do Opportunity Score.

    Combina:
    - Retorno sobre Investimento (ROI)
    - Lucro absoluto em coins
    - Score de liquidez do ativo (0-100)
    - Grau de confiança estatística (LOW, MEDIUM, HIGH)
    - Eficiência de alocação de capital em relação ao tamanho da banca atual
    - Idade da oportunidade
    """

    def calculate(
        self,
        expected_roi: float,
        expected_profit: int,
        buy_price: int,
        liquidity_score: int,
        confidence: str,
        bankroll: int = 5000,
        age_minutes: float | None = 0.0,
    ) -> OpportunityScoreResult:
        if expected_profit <= 0 or expected_roi <= 0.0:
            return OpportunityScoreResult(
                score=0.0,
                roi_component=0.0,
                profit_component=0.0,
                liquidity_component=0.0,
                confidence_component=0.0,
                capital_efficiency_multiplier=0.0,
                recency_multiplier=1.0,
                explanation="Operação sem expectativa de lucro positivo",
            )

        # 1. Componente ROI (0 a 35 pontos) - teto em 50% de ROI
        roi_pts = min(max(0.0, expected_roi) / 0.50, 1.0) * 35.0

        # 2. Componente Lucro Absoluto (0 a 25 pontos) - teto em 1000 coins
        profit_pts = min(max(0, expected_profit) / 1000.0, 1.0) * 25.0

        # 3. Componente Liquidez (0 a 20 pontos)
        liq_pts = (min(max(0, liquidity_score), 100) / 100.0) * 20.0

        # 4. Componente Confiança (0 a 20 pontos)
        conf_map = {"HIGH": 20.0, "MEDIUM": 12.0, "LOW": 4.0}
        conf_pts = conf_map.get(confidence.upper(), 4.0)

        raw_base = roi_pts + profit_pts + liq_pts + conf_pts

        # 5. Multiplicador de Eficiência de Capital (favorece liquidez de banca)
        if bankroll > 0:
            cost_ratio = buy_price / float(bankroll)
            if buy_price > bankroll:
                cap_mult = 0.0  # Inviável para o saldo atual
            elif cost_ratio <= 0.20:
                cap_mult = 1.20  # Excelente rotação de capital
            elif cost_ratio <= 0.40:
                cap_mult = 1.00  # Razoável
            elif cost_ratio <= 0.65:
                cap_mult = 0.80  # Compromete grande fração da banca
            else:
                cap_mult = 0.60  # Risco elevado de prender capital
        else:
            cap_mult = 1.00

        # 6. Multiplicador por Idade da Oportunidade
        age = age_minutes if age_minutes is not None else 0.0
        if age <= 15:
            recency_mult = 1.00
        elif age <= 60:
            recency_mult = 0.90
        elif age <= 120:
            recency_mult = 0.75
        else:
            recency_mult = 0.50

        final_score = round(raw_base * cap_mult * recency_mult, 2)

        explanation = (
            f"Base: {raw_base:.1f} (ROI: {roi_pts:.1f}, Lucro: {profit_pts:.1f}, "
            f"Liq: {liq_pts:.1f}, Conf: {conf_pts:.1f}) × Cap: {cap_mult:.2f} × Rec: {recency_mult:.2f}"
        )

        return OpportunityScoreResult(
            score=max(0.0, final_score),
            roi_component=round(roi_pts, 2),
            profit_component=round(profit_pts, 2),
            liquidity_component=round(liq_pts, 2),
            confidence_component=round(conf_pts, 2),
            capital_efficiency_multiplier=cap_mult,
            recency_multiplier=recency_mult,
            explanation=explanation,
        )
