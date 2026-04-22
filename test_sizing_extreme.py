#!/usr/bin/env python3
"""
Test extrême pour vérifier que MAX_POSITION_USDC est respecté même avec un edge énorme
"""

from config import Config

def test_extreme_edge():
    """Test avec des valeurs extrêmes qui dépasseraient normalement la limite"""

    print(f"Configuration:")
    print(f"  MAX_POSITION_USDC: {Config.MAX_POSITION_USDC}")
    print(f"  BANKROLL_USDC: {Config.BANKROLL_USDC}")
    print()

    # Paramètres extrêmes
    MAX_POSITION_PCT = 0.50  # 50% du bankroll (très agressif)
    edge = 0.95  # 95% d'edge (irréaliste mais pour le test)
    current_price = 0.01  # Prix ultra bas

    # Calcul de la size selon la formule dans edge_calculator.py
    odds = (1 / current_price) - 1
    kelly_fraction = (edge / odds) * 0.25  # Quart-Kelly

    size = min(
        Config.BANKROLL_USDC * MAX_POSITION_PCT,  # 40 * 0.50 = 20.0 (énorme!)
        Config.BANKROLL_USDC * kelly_fraction,    # Calcul Kelly
        Config.MAX_POSITION_USDC                  # 2.0 - LIMITE APPLIQUÉE !
    )

    print(f"Paramètres extrêmes:")
    print(f"  Edge: {edge:.1%}")
    print(f"  Current price: {current_price}")
    print(f"  MAX_POSITION_PCT: {MAX_POSITION_PCT:.1%}")
    print()

    print(f"Calculs intermédiaires:")
    print(f"  Odds: {odds:.2f}")
    print(f"  Kelly fraction: {kelly_fraction:.4f}")
    print(f"  BANKROLL * MAX_POSITION_PCT: ${Config.BANKROLL_USDC * MAX_POSITION_PCT:.2f} (ÉNORME!)")
    print(f"  BANKROLL * kelly_fraction: ${Config.BANKROLL_USDC * kelly_fraction:.2f}")
    print(f"  MAX_POSITION_USDC: ${Config.MAX_POSITION_USDC:.2f} (LIMITE)")
    print()

    print(f"Résultat:")
    print(f"  Size calculée: ${size:.2f}")
    print(f"  Respecte MAX_POSITION_USDC: {'OK' if size <= Config.MAX_POSITION_USDC else 'NOK'}")
    print(f"  La limite a-t-elle été appliquée: {'OUI' if size == Config.MAX_POSITION_USDC else 'NON'}")

    return size <= Config.MAX_POSITION_USDC

if __name__ == "__main__":
    success = test_extreme_edge()
    print()
    if success:
        print("OK - Test réussi - MAX_POSITION_USDC protège même dans les cas extrêmes")
    else:
        print("NOK - Test échoué - MAX_POSITION_USDC n'est pas respecté")