#!/usr/bin/env python3
"""
Script de reset de l'état du bot météo
Vide tous les fichiers de données JSON pour un redémarrage propre
"""

import os
import json

def reset_bot_state():
    """Reset complet de l'état du bot"""
    print("🧹 Reset de l'état du bot météo...")

    data_dir = os.getenv("DATA_DIR", "./data")

    # Créer le répertoire s'il n'existe pas
    os.makedirs(data_dir, exist_ok=True)

    # Fichiers de données à reset
    data_files = [
        'positions.json',
        'signals.json',
        'trade_history.json',
        'forecast_log.json'
    ]

    reset_count = 0

    for filename in data_files:
        file_path = os.path.join(data_dir, filename)

        try:
            # Vider le fichier avec une liste vide
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)

            print(f"✅ Reset: {filename}")
            reset_count += 1

        except Exception as e:
            print(f"❌ Erreur reset {filename}: {e}")

    print(f"\n🎉 Bot state nettoyé: {reset_count}/{len(data_files)} fichiers reset")
    print(f"📁 Répertoire: {os.path.abspath(data_dir)}")

    # Afficher le statut final
    print("\n📊 État final:")
    for filename in data_files:
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"   {filename}: {len(data)} entrées")
            except:
                print(f"   {filename}: erreur lecture")
        else:
            print(f"   {filename}: n'existe pas")

if __name__ == "__main__":
    reset_bot_state()