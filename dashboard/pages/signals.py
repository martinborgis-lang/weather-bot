"""
Page Signaux - Analyse détaillée des signaux de trading
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dashboard.utils.data_loader import (
    load_signals, get_city_flag, format_currency,
    format_percentage, format_timestamp
)
from dashboard.utils.charts import edges_histogram

st.set_page_config(
    page_title="Signaux - Weather Bot",
    page_icon="🎯",
    layout="wide"
)

def create_signals_timeline(signals):
    """Crée une timeline des signaux"""
    if not signals:
        return go.Figure()

    # Préparer les données
    df = pd.DataFrame(signals)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['date'] = df['timestamp'].dt.date

    # Graphique timeline
    fig = go.Figure()

    # Grouper par action
    actions = df['action'].unique() if 'action' in df.columns else ['signal']
    colors = ['#2ca02c', '#d62728', '#ff7f0e', '#1f77b4']

    for i, action in enumerate(actions):
        action_data = df[df['action'] == action] if 'action' in df.columns else df
        fig.add_trace(go.Scatter(
            x=action_data['timestamp'],
            y=action_data['edge_value'] if 'edge_value' in action_data.columns else [0.1] * len(action_data),
            mode='markers',
            name=action,
            marker=dict(
                size=action_data['kelly_size_usdc'] / 10 if 'kelly_size_usdc' in action_data.columns else 8,
                color=colors[i % len(colors)],
                opacity=0.7
            ),
            hovertemplate='<b>%{text}</b><br>' +
                          'Edge: %{y:.3f}<br>' +
                          'Time: %{x}<br>' +
                          '<extra></extra>',
            text=[f"{row.get('city', 'N/A')} - {row.get('action', 'signal')}" for _, row in action_data.iterrows()]
        ))

    fig.update_layout(
        title="🕐 Timeline des Signaux",
        xaxis_title="Temps",
        yaxis_title="Valeur de l'Edge",
        height=400,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font_color='white'
    )

    return fig

def create_city_performance_chart(signals):
    """Crée un graphique de performance par ville"""
    if not signals:
        return go.Figure()

    # Grouper par ville
    city_stats = {}
    for signal in signals:
        city = signal.get('city', 'Unknown')
        if city not in city_stats:
            city_stats[city] = {'count': 0, 'avg_edge': 0, 'total_kelly': 0}

        city_stats[city]['count'] += 1
        city_stats[city]['avg_edge'] += signal.get('edge_value', 0)
        city_stats[city]['total_kelly'] += signal.get('kelly_size_usdc', 0)

    # Calculer moyennes
    for city in city_stats:
        if city_stats[city]['count'] > 0:
            city_stats[city]['avg_edge'] /= city_stats[city]['count']

    if not city_stats:
        return go.Figure()

    # Créer le graphique
    cities = list(city_stats.keys())
    counts = [city_stats[city]['count'] for city in cities]
    avg_edges = [city_stats[city]['avg_edge'] for city in cities]
    total_kelly = [city_stats[city]['total_kelly'] for city in cities]
    city_labels = [f"{get_city_flag(city)} {city}" for city in cities]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=city_labels,
        y=counts,
        name='Nombre de Signaux',
        yaxis='y',
        marker_color='#1f77b4',
        hovertemplate='<b>%{x}</b><br>' +
                      'Signaux: %{y}<br>' +
                      '<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=city_labels,
        y=avg_edges,
        mode='markers+lines',
        name='Edge Moyen',
        yaxis='y2',
        marker=dict(color='#ff7f0e', size=8),
        line=dict(color='#ff7f0e'),
        hovertemplate='<b>%{x}</b><br>' +
                      'Edge Moyen: %{y:.3f}<br>' +
                      '<extra></extra>'
    ))

    fig.update_layout(
        title="🌍 Performance par Ville",
        xaxis_title="Ville",
        yaxis=dict(title="Nombre de Signaux", side='left'),
        yaxis2=dict(title="Edge Moyen", side='right', overlaying='y'),
        height=400,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font_color='white',
        legend=dict(x=0.02, y=0.98)
    )

    return fig

def main():
    st.title("🎯 Analyse des Signaux de Trading")

    # Contrôles de filtre en haut
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        time_periods = {
            "Dernières 6 heures": 6,
            "Dernières 24 heures": 24,
            "Derniers 3 jours": 72,
            "Dernière semaine": 168,
            "Tous": None
        }
        selected_period = st.selectbox("Période", list(time_periods.keys()), index=1)

    with col_filter2:
        # Charger un échantillon pour obtenir les villes disponibles
        sample_signals = load_signals(limit=1000)
        cities = ['Toutes'] + list(set(s.get('city', 'Unknown') for s in sample_signals))
        selected_city = st.selectbox("Ville", cities)

    with col_filter3:
        edge_filter = st.selectbox("Edge minimum", ["Tous", "0.01+", "0.05+", "0.1+", "0.2+"])

    # Charger et filtrer les données
    if time_periods[selected_period]:
        # Calculer la limite basée sur la période
        signals = load_signals(limit=10000)  # Charger beaucoup pour filtrer ensuite
        cutoff_time = datetime.now() - timedelta(hours=time_periods[selected_period])
        signals = [s for s in signals if s.get('timestamp') and
                   datetime.fromisoformat(s['timestamp'].replace('Z', '')) >= cutoff_time]
    else:
        signals = load_signals(limit=10000)

    # Filtrer par ville
    if selected_city != 'Toutes':
        signals = [s for s in signals if s.get('city') == selected_city]

    # Filtrer par edge
    if edge_filter != 'Tous':
        min_edge = float(edge_filter.replace('+', ''))
        signals = [s for s in signals if s.get('edge_value', 0) >= min_edge]

    if not signals:
        st.warning("Aucun signal trouvé avec les filtres sélectionnés")
        st.info("Essayez d'élargir vos critères de recherche")
        return

    # Statistiques globales
    total_signals = len(signals)
    avg_edge = sum(s.get('edge_value', 0) for s in signals) / total_signals if total_signals > 0 else 0
    total_kelly_suggested = sum(s.get('kelly_size_usdc', 0) for s in signals)

    # Signaux par action
    actions = {}
    for signal in signals:
        action = signal.get('action', 'unknown')
        actions[action] = actions.get(action, 0) + 1

    # Métriques en haut
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Signaux Totaux",
            total_signals,
            f"Derniers {selected_period.lower()}"
        )

    with col2:
        st.metric(
            "Edge Moyen",
            f"{avg_edge:.3f}",
            "Plus élevé = meilleur"
        )

    with col3:
        st.metric(
            "Kelly Total Suggéré",
            format_currency(total_kelly_suggested),
            "Taille recommandée"
        )

    with col4:
        most_common_action = max(actions.keys(), key=lambda k: actions[k]) if actions else "N/A"
        st.metric(
            "Action Principale",
            most_common_action,
            f"{actions.get(most_common_action, 0)} fois"
        )

    st.markdown("---")

    # Graphiques principaux
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.plotly_chart(
            edges_histogram(signals),
            use_container_width=True
        )

    with col_chart2:
        st.plotly_chart(
            create_city_performance_chart(signals),
            use_container_width=True
        )

    # Timeline des signaux
    st.plotly_chart(
        create_signals_timeline(signals),
        use_container_width=True
    )

    st.markdown("---")

    # Analyse détaillée
    st.subheader("📊 Analyse Détaillée")

    tab1, tab2, tab3 = st.tabs(["🕐 Signaux Récents", "📈 Trends", "🎯 Top Edges"])

    with tab1:
        st.markdown("### Derniers Signaux Détectés")

        # Trier par timestamp descendant
        recent_signals = sorted(signals, key=lambda x: x.get('timestamp', ''), reverse=True)[:20]

        for i, signal in enumerate(recent_signals):
            edge = signal.get('edge_value', 0)
            edge_emoji = "🔥" if edge > 0.1 else "⚡" if edge > 0.05 else "📊"
            action_emoji = "🟢" if signal.get('action') == 'BUY' else "🔴" if signal.get('action') == 'SELL' else "🔵"

            with st.expander(
                f"{edge_emoji} {get_city_flag(signal.get('city', ''))} {signal.get('city', 'N/A')} - "
                f"Edge {edge:.3f} - {format_timestamp(signal.get('timestamp', ''))}"
            ):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.write("**🎯 Signal**")
                    st.write(f"Action: {action_emoji} {signal.get('action', 'N/A')}")
                    st.write(f"Edge: {edge:.3f}")
                    st.write(f"Confiance: {signal.get('confidence', 0):.2f}")

                with col2:
                    st.write("**💹 Prix**")
                    st.write(f"Marché: {signal.get('market_price', 0):.3f}")
                    st.write(f"Modèle: {signal.get('model_probability', 0):.3f}")
                    st.write(f"Spread: {signal.get('bid_ask_spread', 0):.3f}")

                with col3:
                    st.write("**💰 Kelly**")
                    st.write(f"Taille: {format_currency(signal.get('kelly_size_usdc', 0))}")
                    st.write(f"Fraction: {signal.get('kelly_fraction', 0):.3f}")

                with col4:
                    st.write("**🔍 Détails**")
                    st.write(f"Condition: `{signal.get('condition_id', 'N/A')[:12]}...`")
                    st.write(f"Token: `{signal.get('token_id', 'N/A')[:12]}...`")

    with tab2:
        st.markdown("### Tendances Temporelles")

        if signals:
            # Créer DataFrame pour analyse
            df = pd.DataFrame(signals)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['date'] = df['timestamp'].dt.date

            # Graphique par heure
            hourly_counts = df.groupby('hour').size()

            fig_hourly = go.Figure()
            fig_hourly.add_trace(go.Bar(
                x=hourly_counts.index,
                y=hourly_counts.values,
                marker_color='#17a2b8',
                hovertemplate='Heure: %{x}h<br>Signaux: %{y}<extra></extra>'
            ))

            fig_hourly.update_layout(
                title="📅 Signaux par Heure de la Journée",
                xaxis_title="Heure",
                yaxis_title="Nombre de Signaux",
                height=300,
                paper_bgcolor='#0e1117',
                plot_bgcolor='#0e1117',
                font_color='white'
            )

            st.plotly_chart(fig_hourly, use_container_width=True)

            # Analyse par jour (si assez de données)
            daily_counts = df.groupby('date').size()
            if len(daily_counts) > 1:
                fig_daily = go.Figure()
                fig_daily.add_trace(go.Scatter(
                    x=daily_counts.index,
                    y=daily_counts.values,
                    mode='lines+markers',
                    marker_color='#ff7f0e',
                    hovertemplate='Date: %{x}<br>Signaux: %{y}<extra></extra>'
                ))

                fig_daily.update_layout(
                    title="📈 Évolution Quotidienne des Signaux",
                    xaxis_title="Date",
                    yaxis_title="Nombre de Signaux",
                    height=300,
                    paper_bgcolor='#0e1117',
                    plot_bgcolor='#0e1117',
                    font_color='white'
                )

                st.plotly_chart(fig_daily, use_container_width=True)

    with tab3:
        st.markdown("### Top Edges Détectés")

        # Trier par edge descendant
        top_edges = sorted(signals, key=lambda x: x.get('edge_value', 0), reverse=True)[:10]

        if top_edges:
            st.markdown("**🏆 Top 10 des Meilleurs Edges**")

            for i, signal in enumerate(top_edges, 1):
                edge = signal.get('edge_value', 0)
                kelly = signal.get('kelly_size_usdc', 0)

                col_rank, col_details = st.columns([1, 4])

                with col_rank:
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                    st.markdown(f"### {medal}")

                with col_details:
                    st.write(
                        f"**{get_city_flag(signal.get('city', ''))} {signal.get('city', 'N/A')}** - "
                        f"Edge **{edge:.3f}** - Kelly {format_currency(kelly)} - "
                        f"{format_timestamp(signal.get('timestamp', ''))}"
                    )
        else:
            st.info("Aucun signal avec edge positif trouvé")

if __name__ == "__main__":
    main()