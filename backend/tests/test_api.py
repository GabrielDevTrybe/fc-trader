from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "FC Trader"


def test_full_trading_workflow_e2e(client: TestClient):
    """Teste de integração ponta a ponta simulando o critério de sucesso do MVP:

    1. Inserir lote inicial de observações de Palhinha
    2. Enviar mais observações para compor o preço justo de mercado (1000, 1050, 1100) e 1 outlier (10.000)
    3. Inserir um lance observado a 600
    4. Verificar que 600 gera recomendação BUY com lucro ~397 e ROI > 60%
    5. Listar oportunidades no endpoint /opportunities
    6. Criar e liquidar um Paper Trade de Palhinha
    7. Verificar saldo e progresso da banca
    """
    # 1. Registrar observações de mercado para Palhinha (82)
    batch_market_prices = [
        {"player": "Palhinha", "rating": 82, "price": 1000, "type": "buy_now", "position": "CDM"},
        {"player": "Palhinha", "rating": 82, "price": 1000, "type": "buy_now", "position": "CDM"},
        {"player": "Palhinha", "rating": 82, "price": 1050, "type": "buy_now", "position": "CDM"},
        {"player": "Palhinha", "rating": 82, "price": 1050, "type": "buy_now", "position": "CDM"},
        {"player": "Palhinha", "rating": 82, "price": 1100, "type": "buy_now", "position": "CDM"},
        {"player": "Palhinha", "rating": 82, "price": 10000, "type": "buy_now", "position": "CDM"},  # Outlier!
    ]
    resp_market = client.post("/api/v1/observations", json=batch_market_prices)
    assert resp_market.status_code == 200
    data_market = resp_market.json()
    assert data_market["processed_count"] == 6

    # 2. Registrar oportunidade de lance (bid) a 600 coins
    bid_obs = [
        {"player": "Palhinha", "rating": 82, "price": 600, "type": "bid", "position": "CDM"}
    ]
    resp_bid = client.post("/api/v1/observations", json=bid_obs)
    assert resp_bid.status_code == 200
    data_bid = resp_bid.json()
    analysis = data_bid["analyses"][0]

    assert analysis["player_name"] == "Palhinha"
    assert analysis["recommendation"] == "BUY"
    assert analysis["observed_price"] == 600
    assert 1000 <= analysis["target_sell_price"] <= 1100
    # Net sale de 1050 * 0.95 = 997 -> lucro = 397 coins
    assert analysis["expected_profit"] >= 350
    assert analysis["expected_roi"] > 0.50
    assert analysis["opportunity_score"] > 50

    player_id = analysis["player_id"]

    # 3. Listar oportunidades
    resp_opps = client.get("/api/v1/opportunities")
    assert resp_opps.status_code == 200
    opps = resp_opps.json()
    assert len(opps) >= 1
    palhinha_opp = opps[0]
    assert palhinha_opp["player"]["name"] == "Palhinha"
    assert palhinha_opp["observed_price"] == 600

    # 4. Abrir Paper Trade
    trade_open_payload = {
        "player_id": player_id,
        "buy_price": 600,
        "is_paper_trade": True,
    }
    resp_trade_open = client.post("/api/v1/trades", json=trade_open_payload)
    assert resp_trade_open.status_code == 200
    trade_data = resp_trade_open.json()
    assert trade_data["status"] == "open"
    assert trade_data["buy_price"] == 600
    trade_id = trade_data["id"]

    # 5. Fechar Paper Trade a 1050 coins
    trade_close_payload = {
        "sell_price": 1050,
    }
    resp_trade_close = client.post(f"/api/v1/trades/{trade_id}/close", json=trade_close_payload)
    assert resp_trade_close.status_code == 200
    closed_trade = resp_trade_close.json()
    assert closed_trade["status"] == "sold"
    assert closed_trade["tax"] == 53  # 1050 - 997 = 53
    assert closed_trade["net_received"] == 997
    assert closed_trade["profit"] == 397
    assert closed_trade["roi"] > 0.60

    # 6. Consultar Bankroll
    resp_bankroll = client.get("/api/v1/bankroll?is_paper=true")
    assert resp_bankroll.status_code == 200
    bankroll_data = resp_bankroll.json()
    assert bankroll_data["initial_bankroll"] == 5000
    assert bankroll_data["total_trades"] == 1
    assert bankroll_data["total_profit"] == 397
    assert bankroll_data["win_rate"] == 100.0
    assert bankroll_data["next_target"] == 10000
