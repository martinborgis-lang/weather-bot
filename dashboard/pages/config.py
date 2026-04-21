"""
Page Configuration - Paramètres et état du système
"""

import streamlit as st
import os
import json
from datetime import datetime
from dashboard.utils.data_loader import get_bot_status

st.set_page_config(
    page_title="Configuration - Weather Bot",
    page_icon="⚙️",
    layout="wide"
)

def load_config_from_env():
    """Charge la configuration depuis les variables d'environnement"""
    config = {
        # Trading Config
        'DRY_RUN': os.getenv('DRY_RUN', 'true').lower() == 'true',
        'BANKROLL_USDC': float(os.getenv('BANKROLL_USDC', '250.0')),
        'MAX_POSITION_SIZE_USDC': float(os.getenv('MAX_POSITION_SIZE_USDC', '25.0')),
        'KELLY_MULTIPLIER': float(os.getenv('KELLY_MULTIPLIER', '0.25')),
        'MIN_EDGE_THRESHOLD': float(os.getenv('MIN_EDGE_THRESHOLD', '0.05')),
        'MAX_POSITIONS_PER_MARKET': int(os.getenv('MAX_POSITIONS_PER_MARKET', '3')),

        # Data & Caching
        'DATA_DIR': os.getenv('DATA_DIR', './data'),
        'CACHE_TTL_SECONDS': int(os.getenv('CACHE_TTL_SECONDS', '1800')),

        # API Configuration
        'CLOB_API_URL': os.getenv('CLOB_API_URL', 'https://gamma-api.polymarket.com'),
        'RATE_LIMIT_DELAY': float(os.getenv('RATE_LIMIT_DELAY', '1.2')),

        # Agent Intervals
        'SCANNER_INTERVAL': int(os.getenv('SCANNER_INTERVAL', '300')),
        'FORECASTER_INTERVAL': int(os.getenv('FORECASTER_INTERVAL', '300')),
        'EDGE_DETECTOR_INTERVAL': int(os.getenv('EDGE_DETECTOR_INTERVAL', '180')),
        'POSITION_MANAGER_INTERVAL': int(os.getenv('POSITION_MANAGER_INTERVAL', '60')),
        'TRADE_EXECUTOR_INTERVAL': int(os.getenv('TRADE_EXECUTOR_INTERVAL', '30')),

        # Streamlit
        'PORT': os.getenv('PORT', '8080'),
        'AUTO_REFRESH': True,
    }

    return config

def display_system_status():
    """Affiche l'état du système"""
    st.markdown("### 🖥️ État du Système")

    status = get_bot_status()

    col1, col2, col3 = st.columns(3)

    with col1:
        status_color = {
            "running": "🟢",
            "stopped": "🔴",
            "unknown": "🟡"
        }.get(status, "🟡")

        st.metric(
            "Status Bot",
            f"{status_color} {status.title()}",
            "Basé sur l'activité des fichiers"
        )

    with col2:
        data_dir = os.getenv('DATA_DIR', './data')
        data_exists = os.path.exists(data_dir)
        st.metric(
            "Répertoire Data",
            "✅ Accessible" if data_exists else "❌ Inaccessible",
            data_dir
        )

    with col3:
        # Vérifier les fichiers de données
        data_files = ['positions.json', 'signals.json', 'trade_history.json', 'forecast_log.json']
        existing_files = 0

        for filename in data_files:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                existing_files += 1

        st.metric(
            "Fichiers de Données",
            f"{existing_files}/{len(data_files)}",
            "Fichiers JSON disponibles"
        )

def display_file_info():
    """Affiche les informations sur les fichiers de données"""
    st.markdown("### 📁 Fichiers de Données")

    data_dir = os.getenv('DATA_DIR', './data')
    data_files = {
        'positions.json': 'Positions ouvertes actuelles',
        'signals.json': 'Signaux de trading détectés',
        'trade_history.json': 'Historique complet des trades',
        'forecast_log.json': 'Log des prévisions météo'
    }

    for filename, description in data_files.items():
        filepath = os.path.join(data_dir, filename)

        with st.expander(f"📄 {filename} - {description}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                exists = os.path.exists(filepath)
                st.write(f"**Existe:** {'✅ Oui' if exists else '❌ Non'}")

                if exists:
                    try:
                        size = os.path.getsize(filepath)
                        if size < 1024:
                            size_str = f"{size} bytes"
                        elif size < 1024 * 1024:
                            size_str = f"{size/1024:.1f} KB"
                        else:
                            size_str = f"{size/(1024*1024):.1f} MB"
                        st.write(f"**Taille:** {size_str}")
                    except:
                        st.write("**Taille:** Erreur")

            with col2:
                if exists:
                    try:
                        mtime = os.path.getmtime(filepath)
                        last_modified = datetime.fromtimestamp(mtime)
                        st.write(f"**Modifié:** {last_modified.strftime('%d/%m %H:%M:%S')}")

                        # Calculer l'âge
                        age_seconds = (datetime.now() - last_modified).total_seconds()
                        if age_seconds < 60:
                            age_str = f"{int(age_seconds)}s"
                        elif age_seconds < 3600:
                            age_str = f"{int(age_seconds/60)}min"
                        else:
                            age_str = f"{int(age_seconds/3600)}h"

                        st.write(f"**Âge:** {age_str}")
                    except:
                        st.write("**Modifié:** Erreur")
                        st.write("**Âge:** N/A")

            with col3:
                if exists:
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                st.write(f"**Entrées:** {len(data)}")
                                if data:
                                    st.write(f"**Type:** Liste")
                            elif isinstance(data, dict):
                                st.write(f"**Clés:** {len(data)}")
                                st.write(f"**Type:** Dictionnaire")
                            else:
                                st.write(f"**Type:** {type(data).__name__}")
                    except json.JSONDecodeError:
                        st.write("**Format:** ❌ JSON invalide")
                    except:
                        st.write("**Format:** Erreur lecture")

def display_trading_config(config):
    """Affiche la configuration de trading"""
    st.markdown("### 💰 Configuration Trading")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**💵 Paramètres Financiers**")

        dry_run_color = "warning" if config['DRY_RUN'] else "error"
        st.markdown(f"**Mode:** :{'orange' if config['DRY_RUN'] else 'red'}[{'🧪 DRY RUN' if config['DRY_RUN'] else '💸 LIVE TRADING'}]")

        st.write(f"**Bankroll:** {config['BANKROLL_USDC']:.0f} USDC")
        st.write(f"**Taille max position:** {config['MAX_POSITION_SIZE_USDC']:.0f} USDC")
        st.write(f"**Multiplicateur Kelly:** {config['KELLY_MULTIPLIER']:.2f}")

    with col2:
        st.markdown("**🎯 Paramètres de Trading**")
        st.write(f"**Edge minimum:** {config['MIN_EDGE_THRESHOLD']:.3f}")
        st.write(f"**Max positions/marché:** {config['MAX_POSITIONS_PER_MARKET']}")
        st.write(f"**Rate limit:** {config['RATE_LIMIT_DELAY']:.1f}s")

    # Alertes de configuration
    st.markdown("**⚠️ Alertes Configuration**")

    alerts = []

    if config['DRY_RUN']:
        alerts.append(("info", "Mode DRY_RUN activé - Aucun vrai trade ne sera exécuté"))
    else:
        alerts.append(("error", "Mode LIVE activé - De vraies transactions seront exécutées!"))

    if config['BANKROLL_USDC'] < 100:
        alerts.append(("warning", "Bankroll faible (< 100 USDC)"))

    if config['MIN_EDGE_THRESHOLD'] < 0.02:
        alerts.append(("warning", "Seuil d'edge très bas (< 2%) - Risque de sur-trading"))

    if config['KELLY_MULTIPLIER'] > 0.5:
        alerts.append(("warning", "Multiplicateur Kelly élevé (> 0.5) - Risque accru"))

    for alert_type, message in alerts:
        if alert_type == "info":
            st.info(f"ℹ️ {message}")
        elif alert_type == "warning":
            st.warning(f"⚠️ {message}")
        elif alert_type == "error":
            st.error(f"🚨 {message}")

def display_agent_config(config):
    """Affiche la configuration des agents"""
    st.markdown("### 🤖 Configuration des Agents")

    agents_info = [
        ("Market Scanner", config['SCANNER_INTERVAL'], "Scan des marchés Polymarket", "🔍"),
        ("Weather Forecaster", config['FORECASTER_INTERVAL'], "Prévisions météo ensemble", "🌤️"),
        ("Edge Detector", config['EDGE_DETECTOR_INTERVAL'], "Détection d'opportunités", "⚡"),
        ("Position Manager", config['POSITION_MANAGER_INTERVAL'], "Gestion des positions", "💼"),
        ("Trade Executor", config['TRADE_EXECUTOR_INTERVAL'], "Exécution des trades", "🎯")
    ]

    for name, interval, description, emoji in agents_info:
        with st.expander(f"{emoji} {name} - {interval}s"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Intervalle:** {interval} secondes")
                if interval < 60:
                    frequency = f"Toutes les {interval}s"
                elif interval < 3600:
                    frequency = f"Toutes les {interval//60} minutes"
                else:
                    frequency = f"Toutes les {interval//3600} heures"
                st.write(f"**Fréquence:** {frequency}")

            with col2:
                st.write(f"**Description:** {description}")
                # Recommandations basées sur l'intervalle
                if interval < 30:
                    st.warning("⚠️ Intervalle très court - Risque de rate limiting")
                elif interval > 600:
                    st.info("ℹ️ Intervalle long - Moins réactif")
                else:
                    st.success("✅ Intervalle optimal")

            with col3:
                # Estimation de la charge
                calls_per_hour = 3600 // interval
                st.write(f"**Appels/heure:** ~{calls_per_hour}")

                if name == "Market Scanner" and calls_per_hour > 30:
                    st.warning("⚠️ Charge API élevée")
                elif name == "Trade Executor" and calls_per_hour < 60:
                    st.info("ℹ️ Exécution lente")

def display_advanced_settings(config):
    """Affiche les paramètres avancés"""
    st.markdown("### 🔧 Paramètres Avancés")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**💾 Données & Cache**")
        st.write(f"**Répertoire data:** `{config['DATA_DIR']}`")
        st.write(f"**TTL cache:** {config['CACHE_TTL_SECONDS']}s ({config['CACHE_TTL_SECONDS']//60}min)")

        st.markdown("**🌐 API & Réseau**")
        st.write(f"**URL CLOB API:** `{config['CLOB_API_URL']}`")
        st.write(f"**Rate limit:** {config['RATE_LIMIT_DELAY']:.1f}s")

    with col2:
        st.markdown("**🖥️ Interface**")
        st.write(f"**Port Streamlit:** {config['PORT']}")
        st.write(f"**Auto-refresh:** {'✅ Activé' if config['AUTO_REFRESH'] else '❌ Désactivé'}")

        # Informations système
        st.markdown("**🖥️ Système**")
        try:
            import platform
            st.write(f"**OS:** {platform.system()} {platform.release()}")
            st.write(f"**Python:** {platform.python_version()}")
        except:
            st.write("**OS:** Inconnu")

def main():
    st.title("⚙️ Configuration & État du Système")

    # Charger la configuration
    config = load_config_from_env()

    # Tabs pour organiser les sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🖥️ État Système",
        "💰 Trading",
        "🤖 Agents",
        "📁 Fichiers",
        "🔧 Avancé"
    ])

    with tab1:
        display_system_status()

        st.markdown("---")
        st.markdown("### 🔄 Actions Système")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Actualiser Dashboard", help="Recharger toutes les données"):
                st.rerun()

        with col2:
            if st.button("🧹 Vider Cache", help="Vider le cache Streamlit"):
                st.cache_data.clear()
                st.success("Cache vidé!")

        with col3:
            if st.button("📊 Diagnostics", help="Vérifications système"):
                st.info("Diagnostics complets disponibles dans les autres onglets")

    with tab2:
        display_trading_config(config)

    with tab3:
        display_agent_config(config)

    with tab4:
        display_file_info()

    with tab5:
        display_advanced_settings(config)

        st.markdown("---")
        st.markdown("### 🔧 Variables d'Environnement")

        if st.checkbox("Afficher toutes les variables d'environnement"):
            env_vars = dict(os.environ)
            # Masquer les variables sensibles
            sensitive_patterns = ['key', 'token', 'secret', 'password', 'api']

            for key, value in sorted(env_vars.items()):
                if any(pattern.lower() in key.lower() for pattern in sensitive_patterns):
                    value = "***MASKED***"

                st.text(f"{key} = {value}")

    # Footer avec informations de build
    st.markdown("---")
    st.markdown(
        f'<div style="text-align: center; color: #888; font-size: 0.8rem;">'
        f'Weather Bot Dashboard v1.0 | '
        f'Dernière mise à jour: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'
        f'</div>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()