# Trade Executor Agent

## Vue d'ensemble

Le Trade Executor Agent est responsable de l'exécution des signaux de trading générés par l'Edge Calculator Agent via l'API CLOB de Polymarket.

## Architecture

### Composants principaux

1. **TradeExecutor**: Classe principale qui gère l'exécution des trades
2. **MockClobClient**: Client mock pour les tests et le mode DRY_RUN
3. **Boucle d'exécution**: Process en continu qui traite les signaux toutes les 5 minutes

### Flux de données

```
INPUT:  cache['trade_signals'] = List[TradeSignal]
OUTPUT: cache['executed_trades'] = List[dict] + cache['open_positions'] = List[OpenPosition]
```

## Modes de fonctionnement

### Mode DRY_RUN (Défaut)

- `DRY_RUN=true` dans les variables d'environnement
- Simule les trades sans appeler l'API CLOB réelle
- Logs préfixés par `[DRY RUN]`
- Stocke quand même les positions et trades simulés dans le cache
- `transaction_hash = None` pour les positions simulées

### Mode PRODUCTION

- `DRY_RUN=false` dans les variables d'environnement
- Exécute des trades réels via l'API CLOB Polymarket
- Nécessite des credentials valides
- Récupère le `transaction_hash` réel de la blockchain

## Configuration

### Variables d'environnement (.env)

```bash
# Mode d'exécution
DRY_RUN=true

# Credentials CLOB API Polymarket
CLOB_API_KEY=your_api_key_here
CLOB_SECRET=your_secret_here
CLOB_PASSPHRASE=your_passphrase_here
CLOB_PRIVATE_KEY=your_private_key_here
```

### Constantes

- `EXECUTOR_INTERVAL = 300` secondes (5 minutes)
- Type d'ordre: `FOK` (Fill or Kill)
- Side: Toujours `BUY` (achat de tokens YES)

## Fonctions principales

### `execute_signal(signal: TradeSignal)`

Exécute un signal de trade individuel:

1. **Calcul de la taille**: `size_tokens = recommended_size_usdc / current_price`
2. **Vérification du mode**:
   - DRY_RUN: Log simulé + ordre mock
   - PRODUCTION: Appel `client.create_and_post_order()`
3. **Création de l'OpenPosition**
4. **Stockage dans le cache**

### `process_trade_signals()`

Traite tous les signaux en attente:

1. Récupère `cache['trade_signals']`
2. Pour chaque signal:
   - Vérifie les doublons (pas de position existante sur même market+range)
   - Exécute via `execute_signal()`
3. Vide `cache['trade_signals']` après traitement

### `run_executor_loop()`

Boucle principale:

1. Initialise le ClobClient
2. Boucle infinie toutes les 5 minutes
3. Appelle `process_trade_signals()`
4. Gestion d'erreurs robuste (continue même si un trade échoue)

## Gestion d'erreurs

### Stratégie de récupération

- **Échec d'un trade individuel**: Log erreur et continue avec les autres
- **Échec de l'API CLOB**: Log erreur, pas de crash de l'agent
- **Credentials manquants**: Exception seulement en mode PRODUCTION
- **Erreur de boucle**: Retry après 60 secondes

### Prévention des doublons

- Vérification systématique avant exécution
- Comparaison: `market.condition_id` + `temperature_range.label`
- Skip automatique si position déjà ouverte

## Structure des données

### Ordre CLOB

```python
order_params = {
    "token_id": signal.temperature_range.token_id_yes if signal.side == "YES" else signal.temperature_range.token_id_no,
    "price": signal.temperature_range.current_price,
    "size": recommended_size_usdc / current_price,
    "side": "BUY",
    "order_type": "FOK"
}
```

### OpenPosition créée

```python
OpenPosition(
    market_condition_id=signal.market.condition_id,
    market_title=signal.market.title,
    temperature_label=signal.temperature_range.label,
    side=signal.side,
    entry_price=current_price,
    size_usdc=recommended_size_usdc,
    size_tokens=calculated_size,
    opened_at=datetime.now(),
    transaction_hash=hash_or_none
)
```

### Trade record

```python
{
    "signal": TradeSignal,
    "execution_time": datetime,
    "order_result": dict,
    "position": OpenPosition,
    "dry_run": bool
}
```

## Logs

### Format

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Exemples de logs

#### Mode DRY_RUN
```
[DRY RUN] Exécution: YES 245.2341 tokens (50.00 USDC) sur Highest temperature in London on April 22? - 17°C à 0.2040
```

#### Mode PRODUCTION
```
Trade exécuté: tx_hash=0xabc123..., order_id=order_456
```

## Utilisation

### Intégration dans le système

```python
executor = TradeExecutor()
await executor.run_executor_loop()
```

### Test manuel

```bash
cd /c/Users/marti/meteo
python agents/trade_executor.py
```

## Extensions futures

### CLOB Client réel

Le `MockClobClient` doit être remplacé par la vraie librairie Polymarket CLOB:

```python
# À implémenter
from polymarket_clob import ClobClient

class RealClobClient:
    def __init__(self, api_key, secret, passphrase, private_key):
        self.client = ClobClient(...)

    def create_and_post_order(self, ...):
        return self.client.create_and_post_order(...)
```

### Améliorations possibles

- Support d'autres types d'ordres (LIMIT, GTC)
- Gestion des ordres partiellement remplis
- Monitoring des balances et exposition
- Intégration avec un système de gestion des risques