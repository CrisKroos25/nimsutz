# subscriptions/proration.py
"""
Cálculo de ajustes proporcionales y líneas comerciales (R3, R6, R7, Contratos 7.3).
Moneda GTQ, importes siempre formateados a 2 posiciones decimales ("15.00").
Intervalos [starts_at, ends_at).
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def round_money(amount: Decimal) -> Decimal:
    """Redondea un importe a 2 decimales usando ROUND_HALF_UP (estándar bancario/comercial)."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_upgrade_proration(
    *,
    now: datetime,
    cycle_start: datetime,
    cycle_end: datetime,
    current_price: Decimal,
    target_price: Decimal,
) -> Decimal:
    """
    R6: Cálculo del ajuste proporcional del ciclo en curso al hacer un Upgrade.
    
    1. Duración total del ciclo = (cycle_end - cycle_start).total_seconds()
    2. Tiempo restante = (cycle_end - now).total_seconds()
    3. Fracción restante = max(0, min(1, tiempo_restante / duracion_total))
    4. Crédito no consumido del plan actual = Fracción restante * current_price
    5. Costo proporcional del nuevo plan = Fracción restante * target_price
    6. Ajuste neto = Costo proporcional - Crédito no consumido = Fracción restante * (target_price - current_price)
    """
    total_seconds = Decimal(str((cycle_end - cycle_start).total_seconds()))
    if total_seconds <= 0:
        return Decimal("0.00")

    remaining_seconds = Decimal(str(max(0, (cycle_end - now).total_seconds())))
    fraction = remaining_seconds / total_seconds
    if fraction > 1:
        fraction = Decimal("1")
    elif fraction < 0:
        fraction = Decimal("0")

    price_diff = target_price - current_price
    adjustment = fraction * price_diff
    return round_money(max(Decimal("0.00"), adjustment))

