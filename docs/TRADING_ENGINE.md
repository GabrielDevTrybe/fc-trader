# FC Trader - Motores de Trading e Fórmulas Matemáticas

Este documento detalha o funcionamento determinístico e testável de todos os motores matemáticos e estatísticos que alimentam o FC Trader.

---

## 1. Tax Engine (Taxa EA de 5%)

No mercado de transferências do EA SPORTS FC, a EA retém uma taxa de **5%** sobre o valor bruto de venda de qualquer item. A taxa é calculada com arredondamento para baixo do valor líquido recebido pelo vendedor:

$$\text{net\_sale} = \lfloor \text{sell\_price} \times (1 - \text{tax\_rate}) \rfloor = \lfloor \text{sell\_price} \times 0.95 \rfloor$$
$$\text{tax} = \text{sell\_price} - \text{net\_sale}$$
$$\text{profit} = \text{net\_sale} - \text{buy\_price}$$
$$\text{roi} = \frac{\text{profit}}{\text{buy\_price}}$$

### Regra de Compra Máxima Viável (`max_buy_price`):
Dado um preço alvo estimado de venda ($S$), uma taxa mínima de ROI desejada ($r_{\min}$) e um lucro mínimo absoluto ($p_{\min}$):

$$\text{max\_buy} = \min\left( \left\lfloor \frac{\text{net\_sale}}{1 + r_{\min}} \right\rfloor, \text{net\_sale} - p_{\min} \right)$$

Adicionalmente, nenhuma compra pode exceder o teto de risco de banca:
$$\text{max\_buy} \le \lfloor \text{bankroll} \times \text{max\_bankroll\_pct} \rfloor$$

---

## 2. Market Price Engine & Outliers

O motor de preço justo não considera o menor anúncio isolado como preço representativo.

### Janela Temporal e Decaimento
Observações possuem relevância proporcional ao seu frescor. Consideramos amostras dentro de uma janela de tempo (padrão 24 horas), atribuindo peso com decaimento exponencial:
$$w_i = e^{-\frac{\Delta t_i}{\tau}}$$
onde $\Delta t_i$ é o tempo transcorrido em horas e $\tau$ é a meia-vida configurada (ex: 6 horas).

### Remoção Determinística de Outliers
Quando há pelo menos 4 observações ($N \ge 4$):
1. Ordena-se a amostra de preços: $P = [p_1, p_2, \dots, p_N]$.
2. Calcula-se o 1º quartil ($Q_1$), a mediana e o 3º quartil ($Q_3$).
3. Intervalo interquartil: $IQR = Q_3 - Q_1$.
4. Limites de aceitação:
   $$\text{Lower} = Q_1 - 1.5 \times IQR$$
   $$\text{Upper} = Q_3 + 1.5 \times IQR$$
5. Amostras fora de $[\text{Lower}, \text{Upper}]$ são expurgadas.

### Preço de Mercado Estimado
Calcula-se a média ponderada (ou mediana ponderada) das amostras filtradas.
- **Caso Amostral Baixo ($N < 3$)**: Classificado como `INSUFFICIENT_DATA`. Não são formuladas recomendações de compra até que mais observações sejam adicionadas.

---

## 3. Liquidity Analyzer (Score 0 a 100)

Avalia a facilidade de rotação da carta no mercado através de três subfatores:
1. **Frequência e Volume Recente ($40\%$)**:
   - $N \ge 10$ observações recentes $\rightarrow$ pontuação máxima de volume.
2. **Frescor dos Dados ($30\%$)**:
   - Observação mais recente $< 15$ minutos $\rightarrow$ nota máxima.
   - Observação $> 2$ horas $\rightarrow$ penalidade progressiva.
3. **Estabilidade de Preço ($30\%$)**:
   - Coeficiente de variação $CV = \frac{\sigma}{\mu}$.
   - $CV \le 0.05$ (variação menor que 5%) indica alta estabilidade de liquidez.

---

## 4. Opportunity Score (Score Composto Orientado à Banca)

Classificação para ordenação das oportunidades de trading. Em vez de ordenar apenas por ROI percentual ou lucro em coins, o score equilibra o tamanho da banca atual:

$$\text{OpportunityScore} = \text{base\_score} \times \text{capital\_efficiency\_multiplier} \times \text{recency\_multiplier}$$

Onde:
- $\text{Score}_{\text{roi}} = \min\left(\frac{\text{ROI}}{0.40}, 1.0\right) \times 35$
- $\text{Score}_{\text{profit}} = \min\left(\frac{\text{profit}}{800}, 1.0\right) \times 25$
- $\text{Score}_{\text{liquidity}} = \left(\frac{\text{liquidity\_score}}{100}\right) \times 20$
- $\text{Score}_{\text{confidence}} = \text{confidence\_factor} \times 20$
- **Eficiência de Capital**:
  - Se $\text{buy\_price} \le 0.20 \times \text{bankroll}$: bônus de agilidade (multiplicador até $1.2\times$).
  - Se $\text{buy\_price} > 0.50 \times \text{bankroll}$: penalidade por risco de concentração de capital (multiplicador até $0.7\times$).
