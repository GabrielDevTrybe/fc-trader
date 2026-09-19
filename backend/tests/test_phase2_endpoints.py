from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import Player, PriceObservation, TradingGoal, Trade, BankrollHistory


def test_phase2_api_full_flow(client: TestClient, db_session: Session):
    # 1. Obter capital inicial antes do onboarding: deve estar desconfigurado com saldo 0
    res_before = client.get("/api/v1/bankroll/capital?is_paper=false&data_origin=test")
    assert res_before.status_code == 200
    data_before = res_before.json()
    assert data_before["is_configured"] is False
    assert data_before["cash_balance"] == 0

    # 1.1 Recomendação bloqueada antes do onboarding
    res_act_blocked = client.get("/api/v1/actions/current?is_paper=false&data_origin=test")
    assert res_act_blocked.status_code == 200
    assert res_act_blocked.json()["status"] == "BANKROLL_NOT_CONFIGURED"

    # 2. Onboarding explícito: 5.000 saldo inicial -> 10.000 meta
    res_onboard = client.post(
        "/api/v1/bankroll/onboarding?data_origin=test",
        json={"cash_balance": 5000, "target_balance": 10000},
    )
    assert res_onboard.status_code == 200
    data_onboard = res_onboard.json()
    assert data_onboard["is_configured"] is True
    assert data_onboard["cash_balance"] == 5000
    assert data_onboard["total_equity"] == 5000
    assert data_onboard["inventory_cost"] == 0

    # 3. Consultar meta ativa criada pelo onboarding
    res_goal = client.get("/api/v1/goals/active?is_paper=false&data_origin=test")
    assert res_goal.status_code == 200
    goal = res_goal.json()
    assert goal["status"] == "ACTIVE"
    assert goal["starting_balance"] == 5000
    assert goal["target_balance"] == 10000
    goal_id = goal["id"]

    # 4. Inserir dados de cotação com clube e versão
    batch_obs = [
        {"player": "Atleta Teste", "rating": 83, "price": 1000, "type": "buy_now", "position": "CDM", "club": "Bayern", "data_origin": "test"},
        {"player": "Atleta Teste", "rating": 83, "price": 1050, "type": "buy_now", "position": "CDM", "club": "Bayern", "data_origin": "test"},
        {"player": "Atleta Teste", "rating": 83, "price": 1000, "type": "buy_now", "position": "CDM", "club": "Bayern", "data_origin": "test"},
        {"player": "Atleta Teste", "rating": 83, "price": 600, "type": "bid", "position": "CDM", "club": "Bayern", "data_origin": "test"},
    ]
    resp_obs = client.post("/api/v1/observations", json=batch_obs)
    assert resp_obs.status_code == 200

    # 5. Consultar Ação Atual desbloqueada
    res_act = client.get("/api/v1/actions/current?is_paper=false&data_origin=test")
    assert res_act.status_code == 200
    action_data = res_act.json()
    assert action_data["has_action"] is True
    rec = action_data["action"]
    assert rec is not None
    assert rec["card_id"] is not None
    assert rec["card_club"] == "Bayern"
    assert rec["max_buy_price"] > 0
    assert rec["target_sell_price"] > rec["max_buy_price"]
    assert rec["recommended_quantity"] >= 1
    rec_id = rec["id"]

    # 6. Enviar Feedback BOUGHT com 2 compras a preços distintos
    feedback_payload = {
        "recommendation_id": rec_id,
        "action_result": "BOUGHT",
        "purchases": [
            {"buy_price": rec["max_buy_price"]},
            {"buy_price": rec["max_buy_price"] - 50},
        ],
    }
    fb_res = client.post("/api/v1/actions/feedback?data_origin=test", json=feedback_payload)
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["quantity_bought"] == 2

    # Verificar atualização do capital após compras
    total_spent = rec["max_buy_price"] + (rec["max_buy_price"] - 50)
    res_cap = client.get("/api/v1/bankroll/capital?is_paper=false&data_origin=test")
    cap_after_buy = res_cap.json()
    assert cap_after_buy["cash_balance"] == 5000 - total_spent
    assert cap_after_buy["inventory_cost"] == total_spent
    assert cap_after_buy["total_equity"] == 5000  # Permutação patrimonial intacta!

    # 7. Listar trades abertos vinculados à meta
    res_trades = client.get("/api/v1/trades?status=open&data_origin=test")
    assert res_trades.status_code == 200
    open_trades = res_trades.json()
    assert len(open_trades) == 2
    for t in open_trades:
        assert t["trading_goal_id"] == goal_id
        assert t["card_id"] == rec["card_id"]

    # 8. Vender as duas cartas no preço alvo
    target_sell = rec["target_sell_price"]
    for t in open_trades:
        client.post(f"/api/v1/trades/{t['id']}/close", json={"sell_price": target_sell})

    # Verificar capital e meta após vendas
    res_cap_sold = client.get("/api/v1/bankroll/capital?is_paper=false&data_origin=test")
    cap_after_sold = res_cap_sold.json()
    assert cap_after_sold["inventory_cost"] == 0
    assert cap_after_sold["total_equity"] > 5000

    # 9. Sincronização manual de saldo (5.430 coins) sem gerar trading profit
    res_sync = client.post(
        "/api/v1/bankroll/sync?data_origin=test",
        json={"current_actual_balance": 5430, "reason": "Sincronização manual com o app", "is_paper": False},
    )
    assert res_sync.status_code == 200
    sync_data = res_sync.json()
    assert sync_data["new_balance"] == 5430

    res_cap_reconciled = client.get("/api/v1/bankroll/capital?is_paper=false&data_origin=test")
    cap_rec = res_cap_reconciled.json()
    assert cap_rec["cash_balance"] == 5430
    assert cap_rec["total_trading_profit"] == cap_after_sold["total_trading_profit"]  # Não alterado!
