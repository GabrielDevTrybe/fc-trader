import math
import pytest
from app.engines.tax import (
    calculate_net_sale,
    calculate_tax,
    calculate_profit,
    calculate_roi,
    calculate_max_buy_price,
)


def test_ea_fc_5_percent_tax():
    # 1.000 coins -> 5% taxa = 50 coins, líquido = 950 coins
    assert calculate_net_sale(1000) == 950
    assert calculate_tax(1000) == 50

    # Arredondamento para baixo com valores ímpares:
    # 650 * 0.95 = 617.5 -> floor = 617. Taxa = 650 - 617 = 33
    assert calculate_net_sale(650) == 617
    assert calculate_tax(650) == 33

    # Preço zero ou negativo
    assert calculate_net_sale(0) == 0
    assert calculate_tax(0) == 0


def test_profit_calculation():
    # Compra a 600, Venda a 1000 -> Líquido 950 -> Lucro +350
    profit = calculate_profit(buy_price=600, sell_price=1000)
    assert profit == 350

    # Compra a 1000, Venda a 1000 -> Líquido 950 -> Prejuízo -50
    loss = calculate_profit(buy_price=1000, sell_price=1000)
    assert loss == -50


def test_roi_calculation():
    # Compra a 600, Venda a 1000 -> Lucro 350 -> ROI = 350 / 600 = 58.33%
    roi = calculate_roi(buy_price=600, sell_price=1000)
    assert pytest.approx(roi, 0.001) == 350 / 600

    # Compra inválida <= 0
    assert calculate_roi(0, 1000) == 0.0


def test_max_buy_price_constraints():
    # Venda alvo: 1.000 -> Líquido: 950
    # Min profit = 100 -> teto por lucro = 950 - 100 = 850
    # Min ROI = 15% (0.15) -> teto por ROI = floor(950 / 1.15) = 826
    # Sem restrição de banca -> menor entre os dois = 826
    max_buy = calculate_max_buy_price(
        target_sell_price=1000,
        min_profit=100,
        min_roi=0.15,
        bankroll=None,
    )
    assert max_buy == 826

    # Com restrição de banca: banca = 4000, max 20% = 800
    # min(826, 800) = 800
    max_buy_bankroll = calculate_max_buy_price(
        target_sell_price=1000,
        min_profit=100,
        min_roi=0.15,
        bankroll=4000,
        max_bankroll_percentage=0.20,
    )
    assert max_buy_bankroll == 800
