"""
Script de validação End-to-End (E2E) da Fase 2 do FC Trader.
Valida o ciclo completo de Metas, StrategyEngine, ActionEngine,
feedback de compras múltiplas, contabilidade sem dupla dedução e ajustes externos.
"""
import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000/api/v1"

def req(path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTP ERROR {e.code} on {method} {path}: {err_msg}", file=sys.stderr)
        raise

def run_e2e():
    print("================================================================")
    print("INICIANDO VALIDAÇÃO E2E - FC TRADER FASE 2")
    print("================================================================")

    # 1. Cleanup de dados de teste anteriores
    clean_resp = req("/dev/cleanup-test-data", method="POST")
    print("[1/10] Dev Cleanup (apenas data_origin='test'):", clean_resp["status"])

    # Encerra eventuais trades abertos residuais de testes anteriores para começar com estoque zerado
    dangling_trades = req("/trades?is_paper=true&status=open")
    for dt in dangling_trades:
        req(f"/trades/{dt['id']}/close", method="POST", data={"sell_price": dt["buy_price"]})

    # 2. Consultar Capital Inicial
    cap_initial = req("/bankroll/capital?is_paper=true")
    print(f"[2/10] Capital Inicial (Paper): cash={cap_initial['cash_balance']:,}, inventory={cap_initial['inventory_cost']:,}, equity={cap_initial['total_equity']:,}, available={cap_initial['available_cash']:,}")
    assert cap_initial["available_cash"] == cap_initial["cash_balance"], "available_cash deve ser idêntico a cash_balance"
    assert cap_initial["total_equity"] == cap_initial["cash_balance"] + cap_initial["inventory_cost"], "total_equity = cash + inventory"
    assert cap_initial["inventory_cost"] == 0, "inventory_cost inicial deve ser 0"

    # 3. Criar ou Obter Meta Ativa
    active_goal = req("/goals/active?is_paper=true")
    if active_goal:
        # Se já existe meta de teste, fecha ela para começar ciclo limpo
        req(f"/goals/{active_goal['id']}/close", method="POST")

    current_equity = cap_initial["total_equity"]
    target_equity = current_equity + 5000
    new_goal = req("/goals", method="POST", data={
        "target_balance": target_equity,
        "starting_balance": current_equity,
        "is_paper": True
    })
    goal_id = new_goal["id"]
    print(f"[3/10] Meta Criada com Sucesso: ID={goal_id} | Início={new_goal['starting_balance']:,} -> Alvo={new_goal['target_balance']:,} coins")
    assert new_goal["status"] == "ACTIVE"

    # 4. Inserir Observações de Mercado (Palhinha 83, Buy Now 1000, 1050, 1000; Bid 600)
    batch_obs = [
        {"player": "João Palhinha", "rating": 83, "price": 1000, "type": "buy_now", "position": "CDM", "club": "Bayern", "data_origin": "test"},
        {"player": "João Palhinha", "rating": 83, "price": 1050, "type": "buy_now", "position": "CDM", "club": "Bayern", "data_origin": "test"},
        {"player": "João Palhinha", "rating": 83, "price": 1000, "type": "buy_now", "position": "CDM", "club": "Bayern", "data_origin": "test"},
        {"player": "João Palhinha", "rating": 83, "price": 600, "type": "bid", "position": "CDM", "club": "Bayern", "data_origin": "test"},
    ]
    obs_res = req("/observations", method="POST", data=batch_obs)
    print(f"[4/10] Observações Ingeridas: {obs_res['processed_count']} cotações processadas")

    # 5. Consultar Ação Atual Recomendada pelo ActionEngine
    action_res = req("/actions/current?is_paper=true")
    print(f"[5/10] ActionEngine Resposta: has_action={action_res['has_action']}, status={action_res['status']}")
    assert action_res["has_action"] is True, "Deve haver uma recomendação de compra ativa"
    action = action_res["action"]
    print(f"       -> Jogador: {action['player_name']} ({action['player_rating']})")
    print(f"       -> Estratégia: {action['strategy_name']}")
    print(f"       -> Quantidade Recomendada: {action['recommended_quantity']}x")
    print(f"       -> Preço Teto Compra: {action['max_buy_price']:,} coins")
    print(f"       -> Alvo de Venda: {action['target_sell_price']:,} coins")
    print(f"       -> Lucro Estimado: +{action['estimated_total_profit']:,} coins (ROI {action['estimated_roi']:.1f}%)")
    print(f"       -> Explicação Factual: \"{action['why_explanation']}\"")
    action_id = action["id"]

    # 6. Registrar Feedback de Compra Parcial com Múltiplos Preços
    # Compra de 2 cartas: 1 por 600 e 1 por 550
    feedback_payload = {
        "recommendation_id": action_id,
        "action_result": "BOUGHT",
        "purchases": [
            {"buy_price": 600},
            {"buy_price": 550}
        ]
    }
    fb_res = req("/actions/feedback", method="POST", data=feedback_payload)
    print(f"[6/10] Feedback Enviado: result={fb_res['action_result']}, cartas compradas={fb_res['quantity_bought']}")
    assert fb_res["quantity_bought"] == 2

    # 7. Validar Contabilidade Após Compras (Permutação Patrimonial Sem Dupla Dedução)
    cap_after_buy = req("/bankroll/capital?is_paper=true")
    spent = 600 + 550  # 1150
    print(f"[7/10] Capital Pós-Compra: cash={cap_after_buy['cash_balance']:,}, inventory={cap_after_buy['inventory_cost']:,}, equity={cap_after_buy['total_equity']:,}, available={cap_after_buy['available_cash']:,}")
    assert cap_after_buy["inventory_cost"] == spent, f"inventory_cost deve ser {spent}"
    assert cap_after_buy["cash_balance"] == cap_initial["cash_balance"] - spent, "cash_balance deve deduzir exatamente o gasto"
    assert cap_after_buy["total_equity"] == cap_initial["total_equity"], "total_equity deve permanecer idêntico na compra (troca de caixa por estoque)"
    assert cap_after_buy["available_cash"] == cap_after_buy["cash_balance"], "available_cash deve ser estritamente igual a cash_balance"

    # 8. Listar e Fechar Trades Abertos Vinculados à Meta
    open_trades = req(f"/trades?is_paper=true&status=open&goal_id={goal_id}")
    print(f"[8/10] Posições Abertas em Estoque: {len(open_trades)} cartas")
    assert len(open_trades) == 2
    for t in open_trades:
        assert t["trading_goal_id"] == goal_id, "Trade deve estar vinculado ao ciclo da meta"
        # Vende a 1000 coins cada
        close_res = req(f"/trades/{t['id']}/close", method="POST", data={"sell_price": 1000})
        # 1000 * 0.95 = 950 líquido
        expected_profit = 950 - t["buy_price"]
        assert close_res["profit"] == expected_profit

    # 9. Validar Contabilidade Pós-Venda e Sincronização da Meta
    cap_after_sell = req("/bankroll/capital?is_paper=true")
    # Lucro das 2 vendas: (950 - 600 = 350) + (950 - 550 = 400) = +750 coins
    cycle_profit = 750
    print(f"[9/10] Capital Pós-Venda: cash={cap_after_sell['cash_balance']:,}, inventory={cap_after_sell['inventory_cost']:,}, equity={cap_after_sell['total_equity']:,}")
    assert cap_after_sell["inventory_cost"] == 0, "Estoque zerado após venda de todas as posições"
    assert cap_after_sell["total_equity"] == cap_initial["total_equity"] + cycle_profit, "total_equity deve crescer exatamente pelo lucro realizado"

    goal_sync = req("/goals/active?is_paper=true")
    print(f"       -> Meta Sincronizada: saldo={goal_sync['current_balance']:,}, lucro_meta=+{goal_sync['profit_in_goal']:,}, progresso={goal_sync['progress_percentage']:.1f}%")
    assert goal_sync["profit_in_goal"] == cycle_profit, "Lucro da meta deve somar +750 coins"
    assert goal_sync["current_balance"] == cap_after_sell["total_equity"], "current_balance deve bater com total_equity"

    # 10. Ajuste Externo de Moedas (Recompensa Squad Battles: +2000 coins)
    adj_res = req("/bankroll/adjustments", method="POST", data={
        "amount": 2000,
        "adjustment_type": "reward",
        "reason": "Squad Battles Elite 1 Recompensa Semanal",
        "is_paper": True
    })
    print(f"[10/10] Ajuste Externo Registrado: tipo={adj_res['adjustment_type']}, valor=+{adj_res['amount']:,}, novo_saldo={adj_res['new_balance']:,}")
    cap_after_reward = req("/bankroll/capital?is_paper=true")
    assert cap_after_reward["cash_balance"] == cap_after_sell["cash_balance"] + 2000
    assert cap_after_reward["total_trading_profit"] == cap_after_sell["total_trading_profit"], "Lucro de trading NUNCA é poluído por recompensas externas"
    assert cap_after_reward["total_external_adjustments"] == 2000

    print("================================================================")
    print("VALIDAÇÃO E2E DA FASE 2 CONCLUÍDA COM 100% DE SUCESSO!")
    print("================================================================")

if __name__ == "__main__":
    run_e2e()
