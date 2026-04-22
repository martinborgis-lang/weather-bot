#!/usr/bin/env python3
"""
Test simple pour vérifier que le calcul de sizing respecte MAX_POSITION_USDC
"""

from config import Config

def test_sizing_formula():
    """Test direct de la formule de sizing"""

    print(f"Configuration:")
    print(f"  MAX_POSITION_USDC: {Config.MAX_POSITION_USDC}")
    print(f"  BANKROLL_USDC: {Config.BANKROLL_USDC}")
    print()

    # Paramètres du test
    MAX_POSITION_PCT = 0.02  # 2% du bankroll max
    edge = 0.70  # 70% d'edge (énorme)
    current_price = 0.10  # Prix très bas

    # Calcul de la size selon la formule dans edge_calculator.py
    odds = (1 / current_price) - 1
    kelly_fraction = (edge / odds) * 0.25  # Quart-Kelly

    size = min(
        Config.BANKROLL_USDC * MAX_POSITION_PCT,  # 40 * 0.02 = 0.8
        Config.BANKROLL_USDC * kelly_fraction,    # Calcul Kelly
        Config.MAX_POSITION_USDC                  # 2.0 - LIMITE !
    )

    print(f"Calculs intermédiaires:")
    print(f"  Edge: {edge:.1%}")
    print(f"  Current price: {current_price}")
    print(f"  Odds: {odds:.2f}")
    print(f"  Kelly fraction: {kelly_fraction:.4f}")
    print(f"  BANKROLL * MAX_POSITION_PCT: ${Config.BANKROLL_USDC * MAX_POSITION_PCT:.2f}")
    print(f"  BANKROLL * kelly_fraction: ${Config.BANKROLL_USDC * kelly_fraction:.2f}")
    print(f"  MAX_POSITION_USDC: ${Config.MAX_POSITION_USDC:.2f}")
    print()

    print(f"Résultat:")
    print(f"  Size calculée: ${size:.2f}")
    print(f"  Respecte MAX_POSITION_USDC: {'OK' if size <= Config.MAX_POSITION_USDC else 'NOK'}")
    print(f"  Size <= {Config.MAX_POSITION_USDC}: {size <= Config.MAX_POSITION_USDC}")

    return size <= Config.MAX_POSITION_USDC

if __name__ == "__main__":
    success = test_sizing_formula()
    print()
    if success:
        print("✅ Test réussi - La formule de sizing respecte MAX_POSITION_USDC")
    else:
        print("❌ Test échoué - La formule de sizing dépasse MAX_POSITION_USDC")