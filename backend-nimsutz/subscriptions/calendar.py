# subscriptions/calendar.py
"""
Manejo de meses de calendario exactos en America/Guatemala (R4).
Conserva hora y día ancla; maneja meses cortos (febrero, meses de 30 días)
y recuperación del día ancla original en los meses siguientes.
Los periodos se tratan como intervalos semiabiertos: [starts_at, ends_at).
"""
import calendar
from datetime import datetime
from zoneinfo import ZoneInfo

GUATEMALA_TZ = ZoneInfo("America/Guatemala")


def to_guatemala(dt: datetime) -> datetime:
    """Convierte o asegura que el datetime esté localizado en America/Guatemala."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=GUATEMALA_TZ)
    return dt.astimezone(GUATEMALA_TZ)


def add_calendar_months(dt: datetime, months: int = 1, anchor_day: int = None) -> datetime:
    """
    Suma 'months' meses a 'dt' preservando hora, minuto, segundo, microsegundo
    y el día ancla especificado (o el día de dt si anchor_day es None).

    Si el mes resultante tiene menos días que anchor_day (ej. 31 de enero -> febrero),
    se utiliza el último día del mes (28 o 29 de febrero).
    Si luego se suma otro mes, recupera el día ancla (ej. 31 de marzo).
    """
    local_dt = to_guatemala(dt)
    if anchor_day is None:
        anchor_day = local_dt.day

    total_months = local_dt.year * 12 + (local_dt.month - 1) + months
    new_year = total_months // 12
    new_month = (total_months % 12) + 1

    max_days_in_new_month = calendar.monthrange(new_year, new_month)[1]
    new_day = min(anchor_day, max_days_in_new_month)

    return local_dt.replace(year=new_year, month=new_month, day=new_day)


def calculate_cycle_interval(starts_at: datetime, anchor_day: int = None) -> tuple[datetime, datetime]:
    """
    Calcula el intervalo de un ciclo de 1 mes calendario: [starts_at, ends_at).
    """
    starts_local = to_guatemala(starts_at)
    if anchor_day is None:
        anchor_day = starts_local.day
    ends_local = add_calendar_months(starts_local, 1, anchor_day)
    return starts_local, ends_local

