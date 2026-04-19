"""
Composants graphiques réutilisables avec Plotly pour le dashboard météo
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dashboard.utils.data_loader import get_city_flag

# Configuration couleurs pour thème sombre
COLORS = {
    'primary': '#1f77b4',
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ff7f0e',
    'info': '#17a2b8',
    'background': '#0e1117',
    'surface': '#262730',
    'text': '#ffffff'
}

def pnl_line_chart(history: List[Dict[str, Any]], height: int = 400) -> go.Figure:
    """Graphique en ligne du PnL cumulé dans le temps"""
    if not history:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée d'historique disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Préparer les données
    df = pd.DataFrame(history)
    df = df[df['final_pnl'].notna()].copy()  # Seulement les trades fermés

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun trade fermé disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Parser les timestamps et calculer PnL cumulé
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df['cumulative_pnl'] = df['final_pnl'].cumsum()

    # Créer le graphique
    fig = go.Figure()

    # Ligne PnL cumulé
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['cumulative_pnl'],
        mode='lines+markers',
        name='PnL Cumulé',
        line=dict(color=COLORS['primary'], width=3),
        marker=dict(size=6, color=COLORS['primary']),
        hovertemplate='<b>%{y:.2f} USDC</b><br>%{x}<extra></extra>'
    ))

    # Ligne de référence à zéro
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS['text'], opacity=0.5)

    fig.update_layout(
        title=dict(text="📈 Évolution du PnL Cumulé", font=dict(size=20, color=COLORS['text'])),
        xaxis_title="Date",
        yaxis_title="PnL Cumulé (USDC)",
        height=height,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font_color=COLORS['text'],
        hovermode='x unified',
        showlegend=False
    )

    return fig

def edges_histogram(signals: List[Dict[str, Any]], height: int = 400) -> go.Figure:
    """Histogramme de distribution des edges détectés"""
    if not signals:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun signal disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Extraire les edges
    edges = [signal.get('edge_value', 0) for signal in signals if signal.get('edge_value') is not None]

    if not edges:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun edge calculé dans les signaux",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Créer l'histogramme
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=edges,
        nbinsx=20,
        name="Distribution des Edges",
        marker_color=COLORS['info'],
        opacity=0.8,
        hovertemplate='Edge: %{x:.3f}<br>Count: %{y}<extra></extra>'
    ))

    # Ligne verticale pour l'edge moyen
    avg_edge = sum(edges) / len(edges)
    fig.add_vline(x=avg_edge, line_dash="dash", line_color=COLORS['warning'],
                  annotation_text=f"Moyenne: {avg_edge:.3f}")

    fig.update_layout(
        title=dict(text="🎯 Distribution des Edges Détectés", font=dict(size=20, color=COLORS['text'])),
        xaxis_title="Valeur de l'Edge",
        yaxis_title="Fréquence",
        height=height,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font_color=COLORS['text'],
        showlegend=False
    )

    return fig

def cities_heatmap(history: List[Dict[str, Any]], height: int = 400) -> go.Figure:
    """Heatmap de performance par ville"""
    if not history:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée d'historique disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Grouper par ville
    city_stats = {}
    for trade in history:
        if trade.get('final_pnl') is not None:
            city = trade.get('city', 'Unknown')
            if city not in city_stats:
                city_stats[city] = {'pnl': 0, 'trades': 0, 'wins': 0}

            city_stats[city]['pnl'] += trade['final_pnl']
            city_stats[city]['trades'] += 1
            if trade['final_pnl'] > 0:
                city_stats[city]['wins'] += 1

    if not city_stats:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun trade fermé disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Préparer les données pour la heatmap
    cities = list(city_stats.keys())
    pnl_values = [city_stats[city]['pnl'] for city in cities]
    trade_counts = [city_stats[city]['trades'] for city in cities]
    win_rates = [city_stats[city]['wins'] / city_stats[city]['trades'] for city in cities]

    # Ajouter les drapeaux
    city_flags = [f"{get_city_flag(city)} {city}" for city in cities]

    # Créer la heatmap
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=city_flags,
        x=pnl_values,
        orientation='h',
        marker=dict(
            color=pnl_values,
            colorscale=[[0, COLORS['danger']], [0.5, '#ffffff'], [1, COLORS['success']]],
            colorbar=dict(title="PnL (USDC)", titlefont=dict(color=COLORS['text']),
                         tickfont=dict(color=COLORS['text']))
        ),
        hovertemplate='<b>%{y}</b><br>' +
                      'PnL Total: %{x:.2f} USDC<br>' +
                      'Trades: %{customdata[0]}<br>' +
                      'Win Rate: %{customdata[1]:.1%}<extra></extra>',
        customdata=list(zip(trade_counts, win_rates))
    ))

    fig.update_layout(
        title=dict(text="🌍 Performance par Ville", font=dict(size=20, color=COLORS['text'])),
        xaxis_title="PnL Total (USDC)",
        yaxis_title="Ville",
        height=height,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font_color=COLORS['text'],
        showlegend=False
    )

    return fig

def model_winrate_bar(forecast_log: List[Dict[str, Any]], history: List[Dict[str, Any]], height: int = 400) -> go.Figure:
    """Graphique en barres du win rate par modèle de prévision"""
    if not forecast_log and not history:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée de forecast ou d'historique disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Analyser les performances par accord de modèles
    model_stats = {
        'Fort Accord (>75%)': {'wins': 0, 'total': 0},
        'Accord Moyen (50-75%)': {'wins': 0, 'total': 0},
        'Accord Faible (25-50%)': {'wins': 0, 'total': 0},
        'Désaccord (<25%)': {'wins': 0, 'total': 0}
    }

    # Croiser forecast_log avec history pour voir les résultats
    for trade in history:
        if trade.get('final_pnl') is not None:
            # Simuler l'accord basé sur la performance (en attendant vraies données)
            # En réalité, il faudrait croiser avec forecast_log par condition_id
            pnl = trade['final_pnl']

            # Classification artificielle pour la démo
            if abs(pnl) > 5:  # Gros gain/perte = fort accord
                category = 'Fort Accord (>75%)'
            elif abs(pnl) > 2:
                category = 'Accord Moyen (50-75%)'
            elif abs(pnl) > 0.5:
                category = 'Accord Faible (25-50%)'
            else:
                category = 'Désaccord (<25%)'

            model_stats[category]['total'] += 1
            if pnl > 0:
                model_stats[category]['wins'] += 1

    # Calculer les win rates
    categories = []
    win_rates = []
    trade_counts = []

    for category, stats in model_stats.items():
        if stats['total'] > 0:
            categories.append(category)
            win_rates.append(stats['wins'] / stats['total'])
            trade_counts.append(stats['total'])

    if not categories:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun trade analysé disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Créer le graphique en barres
    fig = go.Figure()

    colors = [COLORS['success'] if wr >= 0.5 else COLORS['danger'] for wr in win_rates]

    fig.add_trace(go.Bar(
        x=categories,
        y=win_rates,
        marker_color=colors,
        hovertemplate='<b>%{x}</b><br>' +
                      'Win Rate: %{y:.1%}<br>' +
                      'Trades: %{customdata}<extra></extra>',
        customdata=trade_counts
    ))

    # Ligne de référence à 50%
    fig.add_hline(y=0.5, line_dash="dash", line_color=COLORS['text'], opacity=0.5,
                  annotation_text="Break-even (50%)")

    fig.update_layout(
        title=dict(text="🤖 Win Rate par Accord des Modèles", font=dict(size=20, color=COLORS['text'])),
        xaxis_title="Niveau d'Accord des Modèles",
        yaxis_title="Win Rate",
        height=height,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font_color=COLORS['text'],
        yaxis_tickformat='.0%',
        showlegend=False
    )

    return fig

def positions_pie(positions: List[Dict[str, Any]], height: int = 400) -> go.Figure:
    """Graphique en secteurs de répartition des positions par ville"""
    if not positions:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune position ouverte",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Grouper par ville
    city_exposure = {}
    total_exposure = 0

    for pos in positions:
        city = pos.get('city', 'Unknown')
        size = pos.get('size_usdc', 0)
        city_exposure[city] = city_exposure.get(city, 0) + size
        total_exposure += size

    if total_exposure == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune exposition financière",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COLORS['text'])
        )
        fig.update_layout(
            height=height,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font_color=COLORS['text']
        )
        return fig

    # Préparer les données
    cities = list(city_exposure.keys())
    exposures = list(city_exposure.values())
    city_flags = [f"{get_city_flag(city)} {city}" for city in cities]

    # Créer le pie chart
    fig = go.Figure()

    fig.add_trace(go.Pie(
        labels=city_flags,
        values=exposures,
        hole=0.4,
        marker=dict(
            colors=px.colors.qualitative.Set3[:len(cities)],
            line=dict(color=COLORS['background'], width=2)
        ),
        hovertemplate='<b>%{label}</b><br>' +
                      'Exposition: %{value:.0f} USDC<br>' +
                      'Part: %{percent}<extra></extra>'
    ))

    # Ajouter le montant total au centre
    fig.add_annotation(
        text=f"<b>{total_exposure:.0f}</b><br>USDC<br>Total",
        x=0.5, y=0.5,
        font_size=16,
        font_color=COLORS['text'],
        showarrow=False
    )

    fig.update_layout(
        title=dict(text="💰 Répartition des Positions par Ville", font=dict(size=20, color=COLORS['text'])),
        height=height,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font_color=COLORS['text'],
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.01,
            font=dict(color=COLORS['text'])
        )
    )

    return fig

def create_metric_card(title: str, value: str, delta: Optional[str] = None,
                      delta_color: str = "normal") -> Dict[str, Any]:
    """Utilitaire pour créer des cartes métriques standardisées"""
    return {
        "title": title,
        "value": value,
        "delta": delta,
        "delta_color": delta_color
    }