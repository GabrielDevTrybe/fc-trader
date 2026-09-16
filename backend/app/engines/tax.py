import math


def calculate_net_sale(sell_price: int, tax_rate: float = 0.05) -> int:
    """Calcula o valor líquido recebido após a dedução da taxa oficial EA (5%).

    A EA FC trunca/arredonda o valor líquido para baixo.
    Exemplo: 1000 * 0.95 = 950 coins.
    """
    if sell_price <= 0:
        return 0
    return math.floor(sell_price * (1.0 - tax_rate))


def calculate_tax(sell_price: int, tax_rate: float = 0.05) -> int:
    """Calcula o total de moedas retidas como taxa pela EA."""
    if sell_price <= 0:
        return 0
    return sell_price - calculate_net_sale(sell_price, tax_rate)


def calculate_profit(buy_price: int, sell_price: int, tax_rate: float = 0.05) -> int:
    """Calcula o lucro líquido absoluto em coins de uma operação.

    profit = floor(sell_price * (1 - tax_rate)) - buy_price
    """
    return calculate_net_sale(sell_price, tax_rate) - buy_price


def calculate_roi(buy_price: int, sell_price: int, tax_rate: float = 0.05) -> float:
    """Calcula o Retorno sobre Investimento (ROI) líquido.

    roi = profit / buy_price
    """
    if buy_price <= 0:
        return 0.0
    profit = calculate_profit(buy_price, sell_price, tax_rate)
    return profit / float(buy_price)


def calculate_max_buy_price(
    target_sell_price: int,
    min_profit: int = 100,
    min_roi: float = 0.15,
    bankroll: int | None = None,
    max_bankroll_percentage: float = 0.20,
    tax_rate: float = 0.05,
) -> int:
    """Calcula o preço máximo recomendado de compra para viabilizar o trade.

    Atende simultaneamente:
    1. Lucro líquido >= min_profit
    2. ROI líquido >= min_roi
    3. Teto máximo por operação (se bankroll fornecido) <= bankroll * max_bankroll_percentage
    """
    if target_sell_price <= 0:
        return 0

    net_sale = calculate_net_sale(target_sell_price, tax_rate)

    # 1. max_buy respeitando o ROI mínimo: net_sale / (1 + min_roi)
    max_by_roi = math.floor(net_sale / (1.0 + min_roi))

    # 2. max_buy respeitando o lucro mínimo em coins: net_sale - min_profit
    max_by_profit = net_sale - min_profit

    candidate = min(max_by_roi, max_by_profit)

    # 3. Restrição de gestão de risco de banca (se informada)
    if bankroll is not None and bankroll > 0:
        max_by_bankroll = math.floor(bankroll * max_bankroll_percentage)
        candidate = min(candidate, max_by_bankroll)

    return max(0, candidate)
