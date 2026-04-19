# Position Manager Agent

Agent responsable de la gestion des positions ouvertes : mise à jour des prix, détection des conditions de sortie et clôture des positions.

## Fonctionnalités

### 1. Mise à jour des prix
- Récupère les prix actuels via l'API Polymarket CLOB (`/price`)
- Met à jour `current_price`, `unrealized_pnl` et `unrealized_pnl_pct`
- Fréquence : toutes les 5 minutes

### 2. Conditions de sortie

#### Take Profit Partiel (+40%)
- Déclenche une vente de 50% des tokens quand le PnL atteint +40%
- Marque la position comme `partial_sold = True`
- En mode DRY_RUN : simulation uniquement
- En mode réel : crée un ordre SELL

#### Gel avant résolution (2h)
- Fige les positions 2h avant la résolution du marché
- Évite les transactions de dernière minute risquées

### 3. Persistance
- Sauvegarde automatique dans `positions.json`
- Chargement au démarrage
- Thread-safe avec `asyncio.Lock`

### 4. Monitoring
- Résumé toutes les 30 minutes
- Logs détaillés des actions
- Suivi du PnL total et par position

## Configuration

```python
TAKE_PROFIT_PARTIAL_PCT = 0.40    # +40% → vendre 50%
TIME_BEFORE_RESOLUTION_HOLD = 7200  # 2h avant fin, freeze
POSITION_MANAGER_INTERVAL = 300  # 5 min entre cycles
SUMMARY_INTERVAL = 1800  # 30 min pour résumés
```

## Utilisation

```python
from agents.position_manager import start_position_manager

# Démarrer le gestionnaire
await start_position_manager()
```

## Intégration avec trade_executor

Le Position Manager est conçu pour s'intégrer avec le Trade Executor pour l'exécution des ordres de vente :

```python
async def execute_partial_sell(self, position: OpenPosition):
    # TODO: Intégrer avec trade_executor.py
    # await trade_executor.place_sell_order(position, tokens_to_sell)
```

## Structure des données

Utilise le modèle `OpenPosition` avec le nouveau champ `partial_sold` pour tracker les ventes partielles.

## Logs

- `🎯` Take profit partiel déclenché
- `🔸` Actions DRY_RUN
- `🔒` Position gelée avant résolution
- `📊` Résumés périodiques
- `🔄` Mise à jour des prix