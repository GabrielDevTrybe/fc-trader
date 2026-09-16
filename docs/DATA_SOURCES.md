# FC Trader - Fontes de Dados e Provedores

## 1. Abstração `MarketDataProvider`

O FC Trader utiliza o padrão arquitetural Provider para desacoplar totalmente o motor de trading das origens dos dados de mercado.

```python
class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_observations(self, **kwargs) -> list[PriceObservationCreate]:
        """Obtém observações de preços a partir da fonte."""
        pass
```

---

## 2. Provedores Implementados no MVP

### A. `ManualMarketDataProvider`
- Permite a entrada manual e em lote de observações através do frontend ou do endpoint `POST /api/v1/observations`.
- Focado em agilidade máxima (inserções por digitação rápida ou atalhos de teclado).
- Aceita payloads individuais ou listas de observações.

### B. `CSVMarketDataProvider`
- Permite a importação em lote de observações registradas em planilhas ou arquivos CSV.
- Formato padrão esperado:
  ```csv
  player,rating,price,type,position,league
  Palhinha,82,600,bid,CDM,Premier League
  Savinho,80,650,buy_now,RW,Premier League
  ```

---

## 3. Conformidade e Provedores Futuros

- **Restrições Estritas**: O projeto **não** implementa bots, auto-buyers, scrapers com quebra de proteção ou chamadas a endpoints privados não autorizados da EA.
- **Evolução Permitida**: Caso no futuro existam APIs oficiais ou fontes públicas autorizadas de dados agregados, novos provedores poderão ser implementados derivando de `MarketDataProvider` sem demandar alterações nas engines ou no banco de dados.
