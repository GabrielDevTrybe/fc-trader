import os
import re
from uuid import uuid4
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.entities import Player, PlayerCard, CardExternalId, PriceObservation, BankrollHistory, Trade
from app.services.observation_service import ObservationService
from app.schemas.schemas import ObservationBatchItem, BankrollOnboardingCreate, BankrollSyncCreate
from app.services.bankroll_service import BankrollService


def test_same_player_same_rating_different_clubs(db_session: Session):
    """Garante que a mesma pessoa com mesmo rating em clubes distintos gera CardVersions distintas sem contaminação de preços."""
    service = ObservationService(db_session)

    # 1. Ingestão de Palhinha no Benfica (rating 82, preço ~1000)
    batch_benfica = [
        ObservationBatchItem(player="João Palhinha", rating=82, price=1000, type="buy_now", club="Benfica", league="Liga Portugal", position="CDM", data_origin="test"),
        ObservationBatchItem(player="João Palhinha", rating=82, price=1050, type="buy_now", club="Benfica", league="Liga Portugal", position="CDM", data_origin="test"),
        ObservationBatchItem(player="João Palhinha", rating=82, price=1000, type="buy_now", club="Benfica", league="Liga Portugal", position="CDM", data_origin="test"),
    ]
    resp_benfica = service.process_batch(batch_benfica)
    assert resp_benfica.processed_count == 3

    # 2. Ingestão de Palhinha no Bayern München (rating 82, preço ~3000)
    batch_bayern = [
        ObservationBatchItem(player="João Palhinha", rating=82, price=3000, type="buy_now", club="Bayern München", league="Bundesliga", position="CDM", data_origin="test"),
        ObservationBatchItem(player="João Palhinha", rating=82, price=3100, type="buy_now", club="Bayern München", league="Bundesliga", position="CDM", data_origin="test"),
        ObservationBatchItem(player="João Palhinha", rating=82, price=3000, type="buy_now", club="Bayern München", league="Bundesliga", position="CDM", data_origin="test"),
    ]
    resp_bayern = service.process_batch(batch_bayern)
    assert resp_bayern.processed_count == 3

    # 3. Verificação no banco: 1 Player, 2 PlayerCards distintas
    players = db_session.query(Player).filter(Player.name.ilike("João Palhinha")).all()
    assert len(players) == 1
    player = players[0]

    cards = db_session.query(PlayerCard).filter(PlayerCard.player_id == player.id).all()
    assert len(cards) == 2

    benfica_card = next(c for c in cards if c.club == "Benfica")
    bayern_card = next(c for c in cards if c.club == "Bayern München")

    assert benfica_card.id != bayern_card.id
    assert benfica_card.rating == 82
    assert bayern_card.rating == 82

    # 4. Verificação de preço justo independente (sem contaminação)
    benfica_analysis = resp_benfica.analyses[-1]
    bayern_analysis = resp_bayern.analyses[-1]

    assert benfica_analysis.card_id == benfica_card.id
    assert bayern_analysis.card_id == bayern_card.id
    assert 1000 <= benfica_analysis.market_price <= 1050
    assert 3000 <= bayern_analysis.market_price <= 3100
    assert benfica_analysis.market_price < 1500 < bayern_analysis.market_price


def test_same_card_version_different_platforms_no_duplicate_card(db_session: Session):
    """Garante que mercados diferentes (PC e Console) para a mesma carta usam a mesma CardVersion canônica."""
    service = ObservationService(db_session)

    # Cotação Console
    service.process_batch([
        ObservationBatchItem(player="Bruno Fernandes", rating=87, price=12000, type="buy_now", club="Man United", platform="console", data_origin="test")
    ])

    # Cotação PC
    service.process_batch([
        ObservationBatchItem(player="Bruno Fernandes", rating=87, price=16000, type="buy_now", club="Man United", platform="pc", data_origin="test")
    ])

    # Deve existir estritamente 1 PlayerCard
    cards = db_session.query(PlayerCard).join(Player).filter(Player.name.ilike("Bruno Fernandes")).all()
    assert len(cards) == 1
    card = cards[0]

    # Devem existir 2 observações apontando para a mesma carta, com plataformas diferentes
    observations = db_session.query(PriceObservation).filter(PriceObservation.card_id == card.id).all()
    assert len(observations) == 2
    platforms = {o.platform for o in observations}
    assert platforms == {"console", "pc"}


def test_multiple_external_ids_providers_for_card_version(db_session: Session):
    """Garante que uma CardVersion pode ter múltiplos identificadores externos de diferentes provedores autorizados."""
    player = Player(name="Card Test Player", rating=85, data_origin="test")
    db_session.add(player)
    db_session.flush()

    card = PlayerCard(player_id=player.id, rating=85, rarity="Gold", club="Club A", data_origin="test")
    db_session.add(card)
    db_session.flush()

    # Adiciona 2 provedores distintos
    ext1 = CardExternalId(card_id=card.id, provider="provider_alpha", external_id="alpha_123")
    ext2 = CardExternalId(card_id=card.id, provider="provider_beta", external_id="beta_456")
    db_session.add_all([ext1, ext2])
    db_session.commit()

    db_session.refresh(card)
    assert len(card.external_ids) == 2
    assert {e.provider for e in card.external_ids} == {"provider_alpha", "provider_beta"}

    # Tentativa de duplicar o mesmo provider + external_id deve violar constraint
    duplicate = CardExternalId(card_id=card.id, provider="provider_alpha", external_id="alpha_123")
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_isolation_real_paper_test(client: TestClient, db_session: Session):
    """Garante isolamento absoluto: dados de test nunca contaminam a banca real."""
    # 1. Cria histórico artificial marcado com data_origin="test"
    fake_entry = BankrollHistory(
        balance=999999,
        amount=999999,
        entry_type="initial_deposit",
        reason="Saldo falso de teste",
        is_paper=False,
        data_origin="test",
    )
    db_session.add(fake_entry)
    db_session.commit()

    # 2. Consulta a banca REAL como usuário comum (data_origin="user")
    res = client.get("/api/v1/bankroll/capital?is_paper=false")
    assert res.status_code == 200
    data = res.json()

    # Deve estar completamente isolado (is_configured=False e cash_balance=0)
    assert data["is_configured"] is False
    assert data["cash_balance"] == 0
    assert data["cash_balance"] != 999999

    # 3. Consulta ação atual: não pode recomendar compra baseada em saldo de teste
    res_act = client.get("/api/v1/actions/current?is_paper=false")
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "BANKROLL_NOT_CONFIGURED"


def test_onboarding_and_real_bankroll_flow(client: TestClient):
    """Testa o onboarding obrigatório da banca real (5.000 coins -> 10.000 meta)."""
    # 1. Onboarding
    res = client.post(
        "/api/v1/bankroll/onboarding?data_origin=test",
        json={"cash_balance": 5000, "target_balance": 10000},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_configured"] is True
    assert data["cash_balance"] == 5000
    assert data["total_equity"] == 5000

    # 2. Meta ativa sincronizada
    res_goal = client.get("/api/v1/goals/active?is_paper=false&data_origin=test")
    assert res_goal.status_code == 200
    goal = res_goal.json()
    assert goal["starting_balance"] == 5000
    assert goal["target_balance"] == 10000
    assert goal["current_balance"] == 5000


def test_balance_reconciliation_5000_to_5430_no_trade_profit(client: TestClient, db_session: Session):
    """Testa reconciliação manual: 5.000 -> 5.430. Saldo ajusta para 5.430 e total_trading_profit fica rigorosamente em 0."""
    bankroll_service = BankrollService(db_session)

    # 1. Onboarding inicial de 5.000 coins
    bankroll_service.onboard_bankroll(
        BankrollOnboardingCreate(cash_balance=5000, target_balance=10000),
        data_origin="test",
    )

    cap_before = bankroll_service.get_capital_summary(is_paper=False, data_origin="test")
    assert cap_before.cash_balance == 5000
    assert cap_before.total_trading_profit == 0

    # 2. Usuário informa: 'Meu saldo real agora é: 5.430'
    res_sync = client.post(
        "/api/v1/bankroll/sync?data_origin=test",
        json={"current_actual_balance": 5430, "reason": "Sincronização manual do saldo real", "is_paper": False},
    )
    assert res_sync.status_code == 200
    sync_res = res_sync.json()
    assert sync_res["new_balance"] == 5430
    assert sync_res["reconciliation_delta"] == 430

    # 3. Verificação do balanço patrimonial:
    cap_after = bankroll_service.get_capital_summary(is_paper=False, data_origin="test")
    assert cap_after.cash_balance == 5430
    assert cap_after.total_equity == 5430
    assert cap_after.total_reconciliations == 430

    # GARANTIA CRÍTICA: lucro de trading NÃO é afetado pela reconciliação!
    assert cap_after.total_trading_profit == 0


def test_no_palhinha_hardcoded_in_production_code():
    """Garante que a palavra 'Palhinha' não existe em arquivos de produção (engines, services, endpoints, schemas, frontend components)."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    production_dirs = [
        os.path.join(root_dir, "backend", "app", "engines"),
        os.path.join(root_dir, "backend", "app", "services"),
        os.path.join(root_dir, "backend", "app", "api"),
        os.path.join(root_dir, "backend", "app", "schemas"),
        os.path.join(root_dir, "backend", "app", "models"),
        os.path.join(root_dir, "frontend", "src", "components"),
        os.path.join(root_dir, "frontend", "src", "app"),
        os.path.join(root_dir, "frontend", "src", "lib"),
        os.path.join(root_dir, "frontend", "src", "types"),
    ]

    violations = []
    palhinha_pattern = re.compile(r"palhinha", re.IGNORECASE)

    for p_dir in production_dirs:
        if not os.path.exists(p_dir):
            continue
        for dirpath, _, filenames in os.walk(p_dir):
            if "__pycache__" in dirpath or ".next" in dirpath:
                continue
            for fname in filenames:
                if fname.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                    fpath = os.path.join(dirpath, fname)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, 1):
                            if palhinha_pattern.search(line):
                                violations.append(f"{fpath}:{line_idx} -> {line.strip()}")

    assert len(violations) == 0, f"Encontradas referências a 'Palhinha' no código de produção:\n" + "\n".join(violations)


def test_unconfigured_real_bankroll_blocks_actions_goals_and_sync(client, db_session):
    """Garante que no modo REAL não configurado:
    1. capital-summary retorna is_configured=False
    2. actions/current retorna BANKROLL_NOT_CONFIGURED
    3. Criar meta separadamente é estritamente bloqueado (400)
    4. Sincronizar saldo sem onboarding é estritamente bloqueado (400)
    5. Ajustar moedas sem onboarding é estritamente bloqueado (400)
    6. Onboarding cria conjuntamente saldo + meta e desbloqueia o sistema
    """
    # 1. Checa capital inicial não configurado
    res_cap = client.get("/api/v1/bankroll/capital?is_paper=false&data_origin=test")
    assert res_cap.status_code == 200
    assert res_cap.json()["is_configured"] is False
    assert res_cap.json()["cash_balance"] == 0

    # 2. Checa ação bloqueada com BANKROLL_NOT_CONFIGURED
    res_act = client.get("/api/v1/actions/current?is_paper=false&data_origin=test")
    assert res_act.status_code == 200
    act_data = res_act.json()
    assert act_data["has_action"] is False
    assert act_data["status"] == "BANKROLL_NOT_CONFIGURED"

    # 3. Tentativa de criar meta separadamente é rejeitada
    res_goal = client.post(
        "/api/v1/goals?data_origin=test",
        json={"target_balance": 10000, "is_paper": False},
    )
    assert res_goal.status_code == 400
    assert "onboarding" in res_goal.json()["detail"].lower()

    # 4. Tentativa de sincronizar saldo sem onboarding é rejeitada
    res_sync = client.post(
        "/api/v1/bankroll/sync?data_origin=test",
        json={"current_actual_balance": 5000, "is_paper": False},
    )
    assert res_sync.status_code == 400
    assert "onboarding" in res_sync.json()["detail"].lower()

    # 5. Tentativa de ajuste sem onboarding é rejeitada
    res_adj = client.post(
        "/api/v1/bankroll/adjustments?data_origin=test",
        json={"amount": 1000, "adjustment_type": "reward", "reason": "Squad Battles", "is_paper": False},
    )
    assert res_adj.status_code == 400
    assert "onboarding" in res_adj.json()["detail"].lower()

    # 6. Realização do onboarding obrigatório conjunto (saldo + meta)
    res_onboard = client.post(
        "/api/v1/bankroll/onboarding?data_origin=test",
        json={"cash_balance": 5000, "target_balance": 10000},
    )
    assert res_onboard.status_code == 200
    assert res_onboard.json()["is_configured"] is True
    assert res_onboard.json()["cash_balance"] == 5000

    # Agora a meta ativa existe e sync passa a ser permitido
    res_goal_active = client.get("/api/v1/goals/active?is_paper=false&data_origin=test")
    assert res_goal_active.status_code == 200
    assert res_goal_active.json() is not None
    assert res_goal_active.json()["starting_balance"] == 5000
    assert res_goal_active.json()["target_balance"] == 10000

    res_sync_ok = client.post(
        "/api/v1/bankroll/sync?data_origin=test",
        json={"current_actual_balance": 5430, "is_paper": False},
    )
    assert res_sync_ok.status_code == 200

