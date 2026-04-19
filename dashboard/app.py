"""
Dashboard Streamlit pour le bot météo Polymarket
Interface de monitoring en temps réel
"""

import streamlit as st
import os
from datetime import datetime, timedelta
from dashboard.utils.data_loader import (
    load_positions, load_signals, load_trade_history, load_forecast_log,
    calculate_pnl_metrics, get_bot_status, get_latest_activity,
    format_currency, format_percentage, format_timestamp
)
from dashboard.utils.charts import (
    pnl_line_chart, edges_histogram, cities_heatmap,
    model_winrate_bar, positions_pie, create_metric_card
)

# Configuration de la page
st.set_page_config(
    page_title="Weather Bot Dashboard",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour thème sombre
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }

    .metric-container {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }

    .status-running {
        color: #2ca02c;
    }

    .status-stopped {
        color: #d62728;
    }

    .status-unknown {
        color: #ff7f0e;
    }

    .alert-info {
        background-color: #17a2b8;
        color: white;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }

    .alert-warning {
        background-color: #ff7f0e;
        color: white;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def render_header():
    """Affiche l'en-tête principal du dashboard"""
    st.markdown('<h1 class="main-header">🌦️ Weather Bot Dashboard</h1>', unsafe_allow_html=True)

    # Status du bot
    status = get_bot_status()
    status_color = {
        "running": "status-running",
        "stopped": "status-stopped",
        "unknown": "status-unknown"
    }.get(status, "status-unknown")

    status_emoji = {
        "running": "🟢",
        "stopped": "🔴",
        "unknown": "🟡"
    }.get(status, "🟡")

    status_text = {
        "running": "En fonctionnement",
        "stopped": "Arrêté",
        "unknown": "État inconnu"
    }.get(status, "État inconnu")

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.markdown(
            f'<div class="metric-container" style="text-align: center;">'
            f'<span class="{status_color}" style="font-size: 1.2rem;">'
            f'{status_emoji} Bot: {status_text}'
            f'</span></div>',
            unsafe_allow_html=True
        )

def render_key_metrics():
    """Affiche les métriques clés en haut du dashboard"""
    st.markdown("### 📊 Métriques Clés")

    # Charger les données
    metrics = calculate_pnl_metrics()
    activity = get_latest_activity()
    positions = load_positions()

    # Calculer les métriques d'affichage
    total_pnl = metrics.get('total_pnl', 0)
    pnl_24h = metrics.get('pnl_24h', 0)
    bankroll = metrics.get('bankroll', 250)
    win_rate = metrics.get('win_rate', 0)
    total_trades = metrics.get('total_trades', 0)
    signals_24h = activity.get('signals_24h', 0)
    active_positions = len(positions)
    unrealized_pnl = metrics.get('unrealized_pnl', 0)

    # Affichage en 4 colonnes
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💰 PnL Total",
            value=format_currency(total_pnl),
            delta=format_currency(pnl_24h) + " (24h)",
            delta_color="normal" if pnl_24h >= 0 else "inverse"
        )
        st.metric(
            label="🎯 Win Rate",
            value=format_percentage(win_rate * 100),
            delta=f"{total_trades} trades"
        )

    with col2:
        st.metric(
            label="💵 Bankroll",
            value=format_currency(bankroll),
            delta=format_percentage((total_pnl/bankroll)*100 if bankroll > 0 else 0) + " ROI"
        )
        st.metric(
            label="📈 PnL Non Réalisé",
            value=format_currency(unrealized_pnl),
            delta_color="normal" if unrealized_pnl >= 0 else "inverse"
        )

    with col3:
        st.metric(
            label="📍 Positions Actives",
            value=str(active_positions),
            delta=format_currency(sum(p.get('size_usdc', 0) for p in positions)) + " exposé"
        )
        latest_signal = activity.get('latest_signal')
        last_signal_time = "Jamais" if not latest_signal else format_timestamp(latest_signal.get('timestamp', ''))
        st.metric(
            label="🕐 Dernier Signal",
            value=last_signal_time,
            delta=f"{signals_24h} signaux 24h"
        )

    with col4:
        # Mode trading
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        mode_emoji = "🧪" if dry_run else "💸"
        mode_text = "DRY RUN" if dry_run else "LIVE"
        mode_color = "#ff7f0e" if dry_run else "#2ca02c"

        st.markdown(
            f'<div class="metric-container" style="text-align: center; border-color: {mode_color};">'
            f'<div style="font-size: 0.9rem; color: #888;">Mode Trading</div>'
            f'<div style="font-size: 1.5rem; color: {mode_color};">{mode_emoji} {mode_text}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Data directory info
        data_dir = os.getenv("DATA_DIR", "./data")
        st.markdown(
            f'<div style="font-size: 0.8rem; color: #888; text-align: center; margin-top: 0.5rem;">'
            f'📁 Data: {data_dir}'
            f'</div>',
            unsafe_allow_html=True
        )

def render_live_charts():
    """Affiche les graphiques principaux en temps réel"""
    st.markdown("### 📈 Analyse en Temps Réel")

    # Charger les données
    history = load_trade_history()
    signals = load_signals(limit=100)
    positions = load_positions()
    forecast_log = load_forecast_log()

    # Première ligne de graphiques
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            pnl_line_chart(history),
            use_container_width=True,
            key="pnl_chart"
        )

    with col2:
        st.plotly_chart(
            positions_pie(positions),
            use_container_width=True,
            key="positions_pie"
        )

    # Deuxième ligne de graphiques
    col3, col4 = st.columns(2)

    with col3:
        st.plotly_chart(
            edges_histogram(signals),
            use_container_width=True,
            key="edges_hist"
        )

    with col4:
        st.plotly_chart(
            cities_heatmap(history),
            use_container_width=True,
            key="cities_heatmap"
        )

    # Troisième ligne - graphique large
    st.plotly_chart(
        model_winrate_bar(forecast_log, history),
        use_container_width=True,
        key="model_winrate"
    )

def render_recent_activity():
    """Affiche l'activité récente"""
    st.markdown("### ⚡ Activité Récente")

    # Tabs pour différents types d'activité
    tab1, tab2, tab3 = st.tabs(["🎯 Derniers Signaux", "💼 Positions Ouvertes", "📖 Trades Récents"])

    with tab1:
        signals = load_signals(limit=10)
        if signals:
            for signal in reversed(signals[-5:]):  # 5 derniers signaux
                with st.expander(f"{signal.get('city', 'N/A')} - {format_timestamp(signal.get('timestamp', ''))}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Edge:** {signal.get('edge_value', 0):.3f}")
                        st.write(f"**Type:** {signal.get('action', 'N/A')}")
                    with col2:
                        st.write(f"**Prix Marché:** {signal.get('market_price', 0):.3f}")
                        st.write(f"**Prob Modèle:** {signal.get('model_probability', 0):.3f}")
                    with col3:
                        st.write(f"**Kelly Size:** {signal.get('kelly_size_usdc', 0):.1f} USDC")
                        st.write(f"**Condition:** {signal.get('condition_id', 'N/A')[:12]}...")
        else:
            st.info("Aucun signal récent détecté")

    with tab2:
        positions = load_positions()
        if positions:
            for pos in positions:
                with st.expander(f"{pos.get('city', 'N/A')} - {pos.get('side', 'N/A')} {pos.get('size_usdc', 0):.0f} USDC"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Prix d'entrée:** {pos.get('entry_price', 0):.3f}")
                        st.write(f"**Prix actuel:** {pos.get('current_price', 0):.3f}")
                    with col2:
                        pnl = (pos.get('current_price', 0) - pos.get('entry_price', 0)) * pos.get('size_usdc', 0)
                        if pos.get('side') == 'NO':
                            pnl = -pnl
                        st.write(f"**PnL:** {format_currency(pnl)}")
                        st.write(f"**Ouvert:** {format_timestamp(pos.get('opened_at', ''))}")
                    with col3:
                        st.write(f"**Token:** {pos.get('token_id', 'N/A')[:12]}...")
                        st.write(f"**Date Cible:** {pos.get('target_date', 'N/A')}")
        else:
            st.info("Aucune position ouverte actuellement")

    with tab3:
        history = load_trade_history()
        recent_trades = history[-5:] if history else []  # 5 derniers trades

        if recent_trades:
            for trade in reversed(recent_trades):
                if trade.get('final_pnl') is not None:
                    pnl = trade['final_pnl']
                    pnl_color = "🟢" if pnl > 0 else "🔴"
                    with st.expander(f"{pnl_color} {trade.get('city', 'N/A')} - {format_currency(pnl)}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Side:** {trade.get('side', 'N/A')}")
                            st.write(f"**Size:** {trade.get('size_usdc', 0):.0f} USDC")
                        with col2:
                            st.write(f"**Prix Entrée:** {trade.get('entry_price', 0):.3f}")
                            st.write(f"**Prix Sortie:** {trade.get('exit_price', 0):.3f}")
                        with col3:
                            st.write(f"**Ouvert:** {format_timestamp(trade.get('opened_at', ''))}")
                            st.write(f"**Fermé:** {format_timestamp(trade.get('closed_at', ''))}")
        else:
            st.info("Aucun trade fermé récemment")

def render_sidebar():
    """Affiche la barre latérale avec navigation et contrôles"""
    st.sidebar.markdown("### 🧭 Navigation")

    # Pages disponibles
    pages = {
        "🏠 Accueil": "home",
        "💼 Positions": "positions",
        "🎯 Signaux": "signals",
        "📖 Historique": "history",
        "⚙️ Configuration": "config"
    }

    selected_page = st.sidebar.selectbox(
        "Choisir une page:",
        options=list(pages.keys()),
        index=0
    )

    st.sidebar.markdown("---")

    # Contrôles de refresh
    st.sidebar.markdown("### 🔄 Mise à jour")
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)

    if st.sidebar.button("🔄 Actualiser maintenant"):
        st.rerun()

    # Informations système
    st.sidebar.markdown("### ℹ️ Informations")
    data_dir = os.getenv("DATA_DIR", "./data")
    st.sidebar.text(f"Data dir: {data_dir}")

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    mode_text = "🧪 DRY RUN" if dry_run else "💸 LIVE"
    st.sidebar.text(f"Mode: {mode_text}")

    port = os.getenv("PORT", "8080")
    st.sidebar.text(f"Port: {port}")

    # Timestamp de dernière mise à jour
    st.sidebar.text(f"Màj: {datetime.now().strftime('%H:%M:%S')}")

    # Auto-refresh logic
    if auto_refresh:
        # Utiliser st.empty() avec un timer pour auto-refresh
        import time
        time.sleep(0.1)  # Petite pause pour éviter les refresh trop rapides

    return pages[selected_page]

def main():
    """Fonction principale du dashboard"""
    # Configuration de l'auto-refresh toutes les 30 secondes
    # Note: Dans Streamlit, l'auto-refresh doit être géré côté client avec JavaScript
    # ou en utilisant st.rerun() avec un timer

    # Sidebar navigation
    current_page = render_sidebar()

    # Page d'accueil
    if current_page == "home":
        render_header()
        render_key_metrics()
        st.markdown("---")
        render_live_charts()
        st.markdown("---")
        render_recent_activity()

        # Auto-refresh en bas de page
        st.markdown("---")
        st.markdown(
            '<div style="text-align: center; color: #888; font-size: 0.8rem;">'
            f'Dashboard mis à jour le {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")} | '
            f'Auto-refresh activé (30s)'
            '</div>',
            unsafe_allow_html=True
        )

    elif current_page == "positions":
        # Import et exécution de la page positions
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'pages'))
            import positions
            positions.main()
        except Exception as e:
            st.error(f"Erreur lors du chargement de la page positions: {e}")

    elif current_page == "signals":
        # Import et exécution de la page signals
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'pages'))
            import signals
            signals.main()
        except Exception as e:
            st.error(f"Erreur lors du chargement de la page signals: {e}")

    elif current_page == "history":
        # Import et exécution de la page history
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'pages'))
            import history
            history.main()
        except Exception as e:
            st.error(f"Erreur lors du chargement de la page history: {e}")

    elif current_page == "config":
        # Import et exécution de la page config
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'pages'))
            import config
            config.main()
        except Exception as e:
            st.error(f"Erreur lors du chargement de la page config: {e}")

    else:
        st.error(f"Page '{current_page}' inconnue")

if __name__ == "__main__":
    main()