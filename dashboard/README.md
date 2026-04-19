# Weather Bot Streamlit Dashboard

Interface de monitoring en temps réel pour le bot de trading météo Polymarket.

## 🚀 Démarrage Rapide

```bash
# Lancer le bot + dashboard ensemble
python run_all.py

# Ou lancer seulement le dashboard
streamlit run dashboard/app.py --server.port 8080
```

## 📊 Fonctionnalités

### Page d'Accueil
- **Métriques clés** : PnL total, win rate, positions actives, bankroll
- **Status du bot** : État temps réel basé sur l'activité des fichiers
- **Graphiques interactifs** : PnL cumulé, répartition géographique, distribution des edges
- **Activité récente** : Derniers signaux, positions ouvertes, trades fermés

### Page Positions 💼
- **Vue d'ensemble** : Exposition totale, PnL non réalisé, nombre de positions
- **Répartition géographique** : Graphique en secteurs par ville
- **Table détaillée** : Filtrage par ville/côté, tri par PnL/taille/date
- **Suivi en temps réel** : Prix actuels, PnL calculé en continu

### Page Signaux 🎯
- **Analyse des edges** : Distribution, performance par ville, timeline
- **Filtres avancés** : Par période, ville, edge minimum
- **Top performers** : Meilleurs edges détectés
- **Tendances temporelles** : Signaux par heure/jour

### Page Historique 📖
- **Performance globale** : Métriques complètes (profit factor, drawdown, streaks)
- **Visualisations** : PnL cumulé, performance mensuelle, durée des trades
- **Analyse détaillée** : Filtrage et tri de l'historique complet
- **Statistiques avancées** : Win rate, ROI, analyse des séries

### Page Configuration ⚙️
- **État système** : Status bot, fichiers de données, diagnostics
- **Paramètres trading** : DRY_RUN, bankroll, kelly multiplier
- **Configuration agents** : Intervalles, fréquences, optimisations
- **Fichiers de données** : Taille, âge, validité JSON

## 📁 Architecture des Données

```
/app/data/
├── positions.json      # Positions ouvertes actuelles
├── signals.json        # Signaux de trading détectés
├── trade_history.json  # Historique complet des trades
└── forecast_log.json   # Log des prévisions météo
```

### Flux de Données
1. **Bot** → Écriture des fichiers JSON dans `/app/data/`
2. **Dashboard** → Lecture seule avec cache 30s
3. **Agents** → Mise à jour continue des données

## 🎨 Interface

### Thème Sombre
- Fond : `#0e1117`
- Surface : `#262730`
- Texte : `#ffffff`
- Couleurs : Vert (gains), Rouge (pertes), Bleu (neutre)

### Composants Interactifs
- **Auto-refresh** : 30 secondes configurable
- **Graphiques Plotly** : Zoom, filtres, export
- **Tables filtrables** : Tri, recherche, pagination
- **Métriques temps réel** : Delta coloré, tendances

## ⚡ Performance

### Optimisations
- **Cache Streamlit** : `@st.cache_data(ttl=30)` sur tous les chargements
- **Pagination** : Limitation à 50 éléments par défaut
- **Fichiers JSON** : Rotation automatique (500-1000 entrées max)
- **Graphiques** : Échantillonnage pour gros datasets

### Mémoire
- **Positions** : ~1KB par position
- **Signaux** : ~0.5KB par signal (500 max)
- **Historique** : ~1KB par trade (1000 max)
- **Forecasts** : ~2KB par prévision (1000 max)

## 🔧 Configuration

### Variables d'Environnement
```bash
DATA_DIR=/app/data          # Répertoire des données
PORT=8080                   # Port Streamlit
DRY_RUN=true               # Mode simulation
BANKROLL_USDC=250.0        # Capital de trading
```

### Personnalisation
- **Couleurs** : Modifier `COLORS` dans `dashboard/utils/charts.py`
- **Intervalles** : Changer `ttl` dans les `@st.cache_data`
- **Métriques** : Ajouter calculs dans `dashboard/utils/data_loader.py`

## 📱 Responsive Design

Compatible avec :
- **Desktop** : Layout large 3-4 colonnes
- **Tablet** : Layout adaptatif 2 colonnes
- **Mobile** : Layout vertical 1 colonne

## 🚀 Déploiement Railway

### Configuration Automatique
- **Buildpack** : Nixpacks avec Python 3.9
- **Start Command** : `python run_all.py`
- **Port** : Auto-détection depuis `$PORT`
- **Persistance** : Volume `/app/data`

### Variables Railway
```
DRY_RUN=true
DATA_DIR=/app/data
PORT=$PORT
BANKROLL_USDC=250.0
```

## 🔍 Debug & Monitoring

### Logs
- **Bot** : Logs structurés avec timestamps
- **Dashboard** : Streamlit logs + erreurs custom
- **Données** : Validation JSON avec fallbacks

### Health Checks
- **Bot Status** : Basé sur l'âge des fichiers (< 10min = running)
- **API Status** : Test de connectivité automatique
- **Données** : Vérification intégrité JSON

## 📈 Métriques Disponibles

### Trading
- PnL total/24h, ROI, Profit Factor
- Win Rate, Drawdown Maximum
- Positions actives, Exposition totale

### Performance
- Edges détectés, Signaux traités
- Temps d'exécution, Accord des modèles
- Répartition géographique

### Système
- Utilisation mémoire, Âge des données
- Status API, Erreurs de parsing
- Fréquence de mise à jour