"""
Page Positions - Gestion détaillée des positions ouvertes
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dashboard.utils.data_loader import (
    load_positions, get_city_flag, format_currency,
    format_percentage, format_timestamp
)
from dashboard.utils.charts import positions_pie

st.set_page_config(
    page_title="Positions - Weather Bot",
    page_icon="💼",
    layout="wide"
)

def main():
    st.title("💼 Gestion des Positions")

    # Charger les données
    positions = load_positions()

    if not positions:
        st.warning("Aucune position ouverte actuellement")
        st.info("Les positions apparaîtront ici une fois que le bot aura ouvert des trades")
        return

    # Statistiques globales
    total_exposure = sum(p.get('size_usdc', 0) for p in positions)
    total_unrealized_pnl = 0

    for pos in positions:
        if "current_price" in pos and "entry_price" in pos and "size_usdc" in pos:
            price_change = pos["current_price"] - pos["entry_price"]
            if pos.get("side") == "NO":
                price_change = -price_change
            total_unrealized_pnl += price_change * pos["size_usdc"]

    # Métriques en haut
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Positions Actives",
            len(positions),
            f"{len([p for p in positions if p.get('side') == 'YES'])} YES, {len([p for p in positions if p.get('side') == 'NO'])} NO"
        )

    with col2:
        st.metric(
            "Exposition Totale",
            format_currency(total_exposure),
            delta_color="normal"
        )

    with col3:
        st.metric(
            "PnL Non Réalisé",
            format_currency(total_unrealized_pnl),
            delta_color="normal" if total_unrealized_pnl >= 0 else "inverse"
        )

    with col4:
        roi_unrealized = (total_unrealized_pnl / total_exposure * 100) if total_exposure > 0 else 0
        st.metric(
            "ROI Non Réalisé",
            format_percentage(roi_unrealized),
            delta_color="normal" if roi_unrealized >= 0 else "inverse"
        )

    st.markdown("---")

    # Graphique de répartition
    col_chart, col_table = st.columns([1, 2])

    with col_chart:
        st.plotly_chart(
            positions_pie(positions),
            use_container_width=True
        )

    with col_table:
        st.subheader("📊 Résumé par Ville")

        # Grouper par ville
        city_stats = {}
        for pos in positions:
            city = pos.get('city', 'Unknown')
            if city not in city_stats:
                city_stats[city] = {
                    'positions': 0,
                    'exposure': 0,
                    'unrealized_pnl': 0,
                    'yes_count': 0,
                    'no_count': 0
                }

            city_stats[city]['positions'] += 1
            city_stats[city]['exposure'] += pos.get('size_usdc', 0)

            if pos.get('side') == 'YES':
                city_stats[city]['yes_count'] += 1
            else:
                city_stats[city]['no_count'] += 1

            # Calculer PnL non réalisé
            if "current_price" in pos and "entry_price" in pos and "size_usdc" in pos:
                price_change = pos["current_price"] - pos["entry_price"]
                if pos.get("side") == "NO":
                    price_change = -price_change
                city_stats[city]['unrealized_pnl'] += price_change * pos["size_usdc"]

        # Créer DataFrame pour affichage
        summary_data = []
        for city, stats in city_stats.items():
            summary_data.append({
                'Ville': f"{get_city_flag(city)} {city}",
                'Positions': f"{stats['positions']} ({stats['yes_count']}Y/{stats['no_count']}N)",
                'Exposition': format_currency(stats['exposure']),
                'PnL': format_currency(stats['unrealized_pnl'])
            })

        if summary_data:
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Table détaillée des positions
    st.subheader("📋 Détail des Positions")

    # Filtres
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        cities = ['Toutes'] + list(set(p.get('city', 'Unknown') for p in positions))
        selected_city = st.selectbox("Filtrer par ville", cities)

    with col_filter2:
        sides = ['Tous', 'YES', 'NO']
        selected_side = st.selectbox("Filtrer par côté", sides)

    with col_filter3:
        sort_options = ['Date d\'ouverture', 'Taille', 'PnL', 'Ville']
        sort_by = st.selectbox("Trier par", sort_options)

    # Filtrer les données
    filtered_positions = positions.copy()

    if selected_city != 'Toutes':
        filtered_positions = [p for p in filtered_positions if p.get('city') == selected_city]

    if selected_side != 'Tous':
        filtered_positions = [p for p in filtered_positions if p.get('side') == selected_side]

    # Trier les données
    if sort_by == 'Date d\'ouverture':
        filtered_positions.sort(key=lambda x: x.get('opened_at', ''), reverse=True)
    elif sort_by == 'Taille':
        filtered_positions.sort(key=lambda x: x.get('size_usdc', 0), reverse=True)
    elif sort_by == 'Ville':
        filtered_positions.sort(key=lambda x: x.get('city', ''))
    elif sort_by == 'PnL':
        def calc_pnl(pos):
            if "current_price" in pos and "entry_price" in pos and "size_usdc" in pos:
                price_change = pos["current_price"] - pos["entry_price"]
                if pos.get("side") == "NO":
                    price_change = -price_change
                return price_change * pos["size_usdc"]
            return 0
        filtered_positions.sort(key=calc_pnl, reverse=True)

    # Afficher les positions
    if not filtered_positions:
        st.info("Aucune position ne correspond aux filtres sélectionnés")
    else:
        st.info(f"{len(filtered_positions)} position(s) affichée(s)")

        for i, pos in enumerate(filtered_positions):
            # Calculer le PnL
            unrealized_pnl = 0
            if "current_price" in pos and "entry_price" in pos and "size_usdc" in pos:
                price_change = pos["current_price"] - pos["entry_price"]
                if pos.get("side") == "NO":
                    price_change = -price_change
                unrealized_pnl = price_change * pos["size_usdc"]

            # Couleur selon le PnL
            pnl_emoji = "🟢" if unrealized_pnl >= 0 else "🔴"
            side_emoji = "👆" if pos.get('side') == 'YES' else "👇"

            with st.expander(
                f"{pnl_emoji} {get_city_flag(pos.get('city', ''))} {pos.get('city', 'N/A')} - "
                f"{side_emoji} {pos.get('side', 'N/A')} {pos.get('size_usdc', 0):.0f} USDC - "
                f"{format_currency(unrealized_pnl)}"
            ):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.write("**📊 Détails du Trade**")
                    st.write(f"Side: {pos.get('side', 'N/A')}")
                    st.write(f"Taille: {pos.get('size_usdc', 0):.2f} USDC")
                    st.write(f"Token: `{pos.get('token_id', 'N/A')[:12]}...`")

                with col2:
                    st.write("**💹 Prix & PnL**")
                    st.write(f"Prix d'entrée: {pos.get('entry_price', 0):.4f}")
                    st.write(f"Prix actuel: {pos.get('current_price', 0):.4f}")
                    st.write(f"PnL: {format_currency(unrealized_pnl)}")

                with col3:
                    st.write("**📅 Dates**")
                    st.write(f"Ouvert: {format_timestamp(pos.get('opened_at', ''))}")
                    st.write(f"Cible: {pos.get('target_date', 'N/A')}")

                    # Calculer jours restants
                    if pos.get('target_date'):
                        try:
                            target = datetime.fromisoformat(pos['target_date'].replace('Z', ''))
                            days_left = (target - datetime.now()).days
                            if days_left > 0:
                                st.write(f"Restant: {days_left} jour(s)")
                            else:
                                st.write("**⏰ Échu**")
                        except:
                            st.write("Restant: N/A")

                with col4:
                    st.write("**🎯 Marché**")
                    st.write(f"Ville: {get_city_flag(pos.get('city', ''))} {pos.get('city', 'N/A')}")
                    st.write(f"Condition: `{pos.get('condition_id', 'N/A')[:12]}...`")

                    # Bouton d'action (simulation)
                    if st.button(f"🚨 Fermer position", key=f"close_{i}", help="Fonction non implémentée"):
                        st.warning("Fermeture manuelle non implémentée - le bot gère automatiquement")

if __name__ == "__main__":
    main()