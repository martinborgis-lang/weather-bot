"""
Page Historique - Analyse complète des performances de trading
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from dashboard.utils.data_loader import (
    load_trade_history, get_city_flag, format_currency,
    format_percentage, format_timestamp
)
from dashboard.utils.charts import pnl_line_chart, cities_heatmap, model_winrate_bar

st.set_page_config(
    page_title="Historique - Weather Bot",
    page_icon="📖",
    layout="wide"
)

def calculate_detailed_metrics(history):
    """Calcule des métriques détaillées de performance"""
    if not history:
        return {}

    closed_trades = [t for t in history if t.get('final_pnl') is not None]
    if not closed_trades:
        return {}

    total_pnl = sum(t['final_pnl'] for t in closed_trades)
    winning_trades = [t for t in closed_trades if t['final_pnl'] > 0]
    losing_trades = [t for t in closed_trades if t['final_pnl'] < 0]

    win_rate = len(winning_trades) / len(closed_trades)
    avg_win = sum(t['final_pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['final_pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

    # Calculs avancés
    profit_factor = abs(sum(t['final_pnl'] for t in winning_trades) / sum(t['final_pnl'] for t in losing_trades)) if losing_trades else float('inf')

    # Maximum Drawdown
    cumulative_pnl = []
    running_total = 0
    for trade in sorted(closed_trades, key=lambda x: x.get('closed_at', '')):
        running_total += trade['final_pnl']
        cumulative_pnl.append(running_total)

    max_drawdown = 0
    peak = 0
    for pnl in cumulative_pnl:
        if pnl > peak:
            peak = pnl
        drawdown = peak - pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Streak analysis
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    current_streak_type = None

    for trade in sorted(closed_trades, key=lambda x: x.get('closed_at', '')):
        is_win = trade['final_pnl'] > 0

        if current_streak_type == is_win:
            current_streak += 1
        else:
            if current_streak_type is True and current_streak > max_win_streak:
                max_win_streak = current_streak
            elif current_streak_type is False and current_streak > max_loss_streak:
                max_loss_streak = current_streak

            current_streak = 1
            current_streak_type = is_win

    # Final streak check
    if current_streak_type is True and current_streak > max_win_streak:
        max_win_streak = current_streak
    elif current_streak_type is False and current_streak > max_loss_streak:
        max_loss_streak = current_streak

    return {
        'total_trades': len(closed_trades),
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak,
        'best_trade': max(t['final_pnl'] for t in closed_trades),
        'worst_trade': min(t['final_pnl'] for t in closed_trades)
    }

def create_monthly_performance(history):
    """Crée un graphique de performance mensuelle"""
    closed_trades = [t for t in history if t.get('final_pnl') is not None and t.get('closed_at')]

    if not closed_trades:
        return go.Figure()

    # Grouper par mois
    monthly_data = {}
    for trade in closed_trades:
        try:
            closed_date = datetime.fromisoformat(trade['closed_at'].replace('Z', ''))
            month_key = closed_date.strftime('%Y-%m')

            if month_key not in monthly_data:
                monthly_data[month_key] = {'pnl': 0, 'trades': 0, 'wins': 0}

            monthly_data[month_key]['pnl'] += trade['final_pnl']
            monthly_data[month_key]['trades'] += 1
            if trade['final_pnl'] > 0:
                monthly_data[month_key]['wins'] += 1
        except:
            continue

    if not monthly_data:
        return go.Figure()

    # Créer le graphique
    months = sorted(monthly_data.keys())
    pnl_values = [monthly_data[m]['pnl'] for m in months]
    trade_counts = [monthly_data[m]['trades'] for m in months]
    win_rates = [monthly_data[m]['wins'] / monthly_data[m]['trades'] for m in months]

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('PnL Mensuel', 'Trades et Win Rate'),
        specs=[[{"secondary_y": False}],
               [{"secondary_y": True}]]
    )

    # PnL mensuel
    colors = ['green' if pnl >= 0 else 'red' for pnl in pnl_values]
    fig.add_trace(
        go.Bar(x=months, y=pnl_values, marker_color=colors, name='PnL'),
        row=1, col=1
    )

    # Nombre de trades
    fig.add_trace(
        go.Bar(x=months, y=trade_counts, marker_color='blue', name='Trades'),
        row=2, col=1
    )

    # Win rate
    fig.add_trace(
        go.Scatter(x=months, y=win_rates, mode='lines+markers',
                  marker_color='orange', name='Win Rate'),
        row=2, col=1, secondary_y=True
    )

    fig.update_layout(
        height=600,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font_color='white',
        title="📅 Performance Mensuelle Détaillée"
    )

    return fig

def create_trade_duration_analysis(history):
    """Analyse la durée des trades"""
    closed_trades = [t for t in history if t.get('final_pnl') is not None
                     and t.get('opened_at') and t.get('closed_at')]

    if not closed_trades:
        return go.Figure()

    durations = []
    pnl_values = []

    for trade in closed_trades:
        try:
            opened = datetime.fromisoformat(trade['opened_at'].replace('Z', ''))
            closed = datetime.fromisoformat(trade['closed_at'].replace('Z', ''))
            duration_hours = (closed - opened).total_seconds() / 3600

            durations.append(duration_hours)
            pnl_values.append(trade['final_pnl'])
        except:
            continue

    if not durations:
        return go.Figure()

    fig = go.Figure()

    # Scatter plot durée vs PnL
    colors = ['green' if pnl >= 0 else 'red' for pnl in pnl_values]
    fig.add_trace(go.Scatter(
        x=durations,
        y=pnl_values,
        mode='markers',
        marker=dict(color=colors, opacity=0.7, size=8),
        hovertemplate='Durée: %{x:.1f}h<br>PnL: %{y:.2f} USDC<extra></extra>',
        name='Trades'
    ))

    fig.update_layout(
        title="⏱️ Durée des Trades vs Performance",
        xaxis_title="Durée (heures)",
        yaxis_title="PnL (USDC)",
        height=400,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font_color='white'
    )

    return fig

def main():
    st.title("📖 Historique des Performances")

    # Charger les données
    history = load_trade_history()

    if not history:
        st.warning("Aucun historique de trading disponible")
        st.info("L'historique apparaîtra ici une fois que le bot aura exécuté et fermé des trades")
        return

    # Calculer les métriques détaillées
    metrics = calculate_detailed_metrics(history)

    if not metrics:
        st.warning("Aucun trade fermé dans l'historique")
        st.info("Seuls les trades fermés (avec PnL final) sont analysés")
        return

    # Affichage des métriques principales
    st.markdown("### 📊 Performance Globale")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "PnL Total",
            format_currency(metrics['total_pnl']),
            delta_color="normal" if metrics['total_pnl'] >= 0 else "inverse"
        )
        st.metric(
            "Trades Totaux",
            metrics['total_trades']
        )

    with col2:
        st.metric(
            "Win Rate",
            format_percentage(metrics['win_rate'] * 100),
            f"{int(metrics['win_rate'] * metrics['total_trades'])}W/{metrics['total_trades'] - int(metrics['win_rate'] * metrics['total_trades'])}L"
        )
        st.metric(
            "Profit Factor",
            f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "∞"
        )

    with col3:
        st.metric(
            "Gain Moyen",
            format_currency(metrics['avg_win']),
            delta_color="normal"
        )
        st.metric(
            "Perte Moyenne",
            format_currency(metrics['avg_loss']),
            delta_color="inverse"
        )

    with col4:
        st.metric(
            "Max Drawdown",
            format_currency(-metrics['max_drawdown']),
            delta_color="inverse"
        )
        st.metric(
            "Meilleur Trade",
            format_currency(metrics['best_trade']),
            delta_color="normal"
        )

    # Métriques avancées
    st.markdown("### 🎯 Statistiques Avancées")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"🔥 **Série de Gains Max:** {metrics['max_win_streak']} trades")

    with col2:
        st.warning(f"❄️ **Série de Pertes Max:** {metrics['max_loss_streak']} trades")

    with col3:
        st.error(f"💸 **Pire Trade:** {format_currency(metrics['worst_trade'])}")

    st.markdown("---")

    # Graphiques principaux
    st.markdown("### 📈 Visualisations")

    # Première ligne - PnL et répartition géographique
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            pnl_line_chart(history),
            use_container_width=True
        )

    with col2:
        st.plotly_chart(
            cities_heatmap(history),
            use_container_width=True
        )

    # Deuxième ligne - Performance mensuelle
    st.plotly_chart(
        create_monthly_performance(history),
        use_container_width=True
    )

    # Troisième ligne - Analyse de durée et modèles
    col3, col4 = st.columns(2)

    with col3:
        st.plotly_chart(
            create_trade_duration_analysis(history),
            use_container_width=True
        )

    with col4:
        forecast_log = []  # TODO: Charger depuis load_forecast_log()
        st.plotly_chart(
            model_winrate_bar(forecast_log, history),
            use_container_width=True
        )

    st.markdown("---")

    # Table des trades détaillée
    st.markdown("### 📋 Historique Détaillé des Trades")

    # Filtres
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        cities = ['Toutes'] + list(set(t.get('city', 'Unknown') for t in history))
        selected_city = st.selectbox("Filtrer par ville", cities)

    with col_filter2:
        result_filter = st.selectbox("Résultat", ["Tous", "Gains seulement", "Pertes seulement"])

    with col_filter3:
        sort_options = ["Date de fermeture", "PnL", "Durée", "Taille"]
        sort_by = st.selectbox("Trier par", sort_options)

    # Filtrer les trades fermés
    closed_trades = [t for t in history if t.get('final_pnl') is not None]

    # Appliquer les filtres
    if selected_city != 'Toutes':
        closed_trades = [t for t in closed_trades if t.get('city') == selected_city]

    if result_filter == "Gains seulement":
        closed_trades = [t for t in closed_trades if t['final_pnl'] > 0]
    elif result_filter == "Pertes seulement":
        closed_trades = [t for t in closed_trades if t['final_pnl'] < 0]

    # Trier
    if sort_by == "Date de fermeture":
        closed_trades.sort(key=lambda x: x.get('closed_at', ''), reverse=True)
    elif sort_by == "PnL":
        closed_trades.sort(key=lambda x: x['final_pnl'], reverse=True)
    elif sort_by == "Taille":
        closed_trades.sort(key=lambda x: x.get('size_usdc', 0), reverse=True)
    elif sort_by == "Durée":
        def calc_duration(trade):
            if trade.get('opened_at') and trade.get('closed_at'):
                try:
                    opened = datetime.fromisoformat(trade['opened_at'].replace('Z', ''))
                    closed = datetime.fromisoformat(trade['closed_at'].replace('Z', ''))
                    return (closed - opened).total_seconds()
                except:
                    return 0
            return 0
        closed_trades.sort(key=calc_duration, reverse=True)

    # Afficher les trades
    if not closed_trades:
        st.info("Aucun trade ne correspond aux filtres sélectionnés")
    else:
        st.info(f"{len(closed_trades)} trade(s) fermé(s) affiché(s)")

        for i, trade in enumerate(closed_trades[:50]):  # Limiter à 50 pour les performances
            pnl = trade['final_pnl']
            pnl_emoji = "🟢" if pnl > 0 else "🔴"
            side_emoji = "👆" if trade.get('side') == 'YES' else "👇"

            # Calculer la durée
            duration_str = "N/A"
            if trade.get('opened_at') and trade.get('closed_at'):
                try:
                    opened = datetime.fromisoformat(trade['opened_at'].replace('Z', ''))
                    closed = datetime.fromisoformat(trade['closed_at'].replace('Z', ''))
                    duration_hours = (closed - opened).total_seconds() / 3600

                    if duration_hours < 1:
                        duration_str = f"{int(duration_hours * 60)}min"
                    elif duration_hours < 24:
                        duration_str = f"{duration_hours:.1f}h"
                    else:
                        duration_str = f"{duration_hours/24:.1f}j"
                except:
                    pass

            with st.expander(
                f"{pnl_emoji} {get_city_flag(trade.get('city', ''))} {trade.get('city', 'N/A')} - "
                f"{side_emoji} {format_currency(pnl)} - {duration_str}"
            ):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.write("**💹 Trade Info**")
                    st.write(f"Side: {trade.get('side', 'N/A')}")
                    st.write(f"Taille: {format_currency(trade.get('size_usdc', 0))}")
                    st.write(f"PnL: {format_currency(pnl)}")

                with col2:
                    st.write("**💰 Prix**")
                    st.write(f"Entrée: {trade.get('entry_price', 0):.4f}")
                    st.write(f"Sortie: {trade.get('exit_price', 0):.4f}")

                    # Calculer le ROI
                    roi = (pnl / trade.get('size_usdc', 1)) * 100 if trade.get('size_usdc', 0) > 0 else 0
                    st.write(f"ROI: {format_percentage(roi)}")

                with col3:
                    st.write("**📅 Timing**")
                    st.write(f"Ouvert: {format_timestamp(trade.get('opened_at', ''))}")
                    st.write(f"Fermé: {format_timestamp(trade.get('closed_at', ''))}")
                    st.write(f"Durée: {duration_str}")

                with col4:
                    st.write("**🔍 Détails**")
                    st.write(f"Token: `{trade.get('token_id', 'N/A')[:12]}...`")
                    st.write(f"Condition: `{trade.get('condition_id', 'N/A')[:12]}...`")

                    reason = trade.get('exit_reason', 'Manual')
                    st.write(f"Sortie: {reason}")

        if len(closed_trades) > 50:
            st.info(f"Affichage des 50 premiers trades. {len(closed_trades) - 50} trades supplémentaires disponibles.")

if __name__ == "__main__":
    main()