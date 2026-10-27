# subscriptions/services.py
import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from . import calendar as sub_calendar
from .errors import SubscriptionError
from .models import Plan, PlanVersion, Subscription, SubscriptionPreference, Quote, ScheduledChange
from .proration import calculate_upgrade_proration, round_money

logger = logging.getLogger(__name__)

FREE_PLAN_CODE = "free"
BASIC_PLAN_CODE = "basic"
PREMIUM_PLAN_CODE = "premium"
QUOTE_TTL_MINUTES = 15


def _latest_version(plan):
    # Usa .all() para aprovechar un prefetch si lo hay.
    return max(plan.versions.all(), key=lambda v: v.version_number, default=None)


def get_current_version(plan_code):
    plan = Plan.objects.filter(code=plan_code, is_available=True).first()
    if plan is None:
        raise SubscriptionError("plan_unavailable", "El plan no estÃ¡ disponible.")  # RN-E2-05
    version = _latest_version(plan)
    if version is None:
        raise SubscriptionError(
            "plan_without_version",
            "El plan no tiene condiciones definidas y no puede contratarse.",
        )
    return version


def is_contractable(version):
    # Los planes pagados se pueden cotizar y contratar si el plan estÃ¡ disponible
    return version.plan.is_available and (version.price == 0 or getattr(settings, "PAID_PLANS_ENABLED", True))


def version_payload(version):
    return {
        "plan_code": version.plan.code,
        "name": version.plan.name,
        "description": version.plan.description,
        "version_id": version.pk,
        "price": str(version.price),
        "currency": version.currency,
        "duration_days": version.duration_days,
        "capacity_bytes": version.capacity_bytes,
        "requires_payment": version.price > 0,
        "contractable": is_contractable(version),
    }


def list_catalog():
    items = []
    plans = Plan.objects.filter(is_available=True).prefetch_related("versions").order_by("id")
    for plan in plans:
        version = _latest_version(plan)
        if version is None:
            logger.warning("Plan '%s' estÃ¡ disponible pero no tiene versiones.", plan.code)
            continue  # situaciÃ³n invÃ¡lida: un plan sin condiciones no se publica
        version.plan = plan
        items.append(version_payload(version))
    return items


def resolve_effective_subscription(user, at=None):
    """
    R8: ResoluciÃ³n efectiva de la cobertura. Comprueba expiraciÃ³n de cobertura
    e idempotentemente realiza la transiciÃ³n que corresponda:
    1. Si aÃºn estÃ¡ vigente, devuelve la suscripciÃ³n actual.
    2. Si venciÃ³ y existe un next_cycle pagado, avanza al siguiente ciclo.
    3. Si venciÃ³ y existe un ScheduledChange, aplica el cambio programado.
    4. Si venciÃ³ y no hay ciclo pagado ni cambio, retorna automÃ¡ticamente a Gratis
       (conservando archivos).
    """
    reference_time = at or timezone.now()
    sub = (
        Subscription.objects.select_related("plan_version__plan", "next_cycle_plan_version__plan")
        .filter(user=user, status=Subscription.Status.ACTIVE)
        .first()
    )
    if sub is None:
        return None

    # Si no tiene fecha de vencimiento (plan Gratis), estÃ¡ vigente indefinidamente
    if sub.expires_at is None:
        return sub

    # Si la fecha de vencimiento aÃºn no ha llegado, sigue vigente
    if sub.expires_at > reference_time:
        return sub

    # Cobertura vencida: resolver transiciÃ³n
    with transaction.atomic():
        sub_locked = (
            Subscription.objects.select_for_update()
            .filter(pk=sub.pk, status=Subscription.Status.ACTIVE)
            .first()
        )
        if sub_locked is None or (sub_locked.expires_at and sub_locked.expires_at > reference_time):
            return sub_locked

        # Caso A: HabÃ­a un siguiente ciclo anticipado ya pagado (R5)
        if sub_locked.next_cycle_starts_at and sub_locked.next_cycle_ends_at and sub_locked.next_cycle_plan_version:
            sub_locked.plan_version = sub_locked.next_cycle_plan_version
            sub_locked.started_at = sub_locked.next_cycle_starts_at
            sub_locked.expires_at = sub_locked.next_cycle_ends_at
            sub_locked.coverage_end = sub_locked.next_cycle_ends_at
            sub_locked.next_cycle_starts_at = None
            sub_locked.next_cycle_ends_at = None
            sub_locked.next_cycle_plan_version = None
            sub_locked.save(update_fields=[
                "plan_version", "started_at", "expires_at", "coverage_end",
                "next_cycle_starts_at", "next_cycle_ends_at", "next_cycle_plan_version"
            ])
            # Si el nuevo ciclo cubre la fecha de referencia, devolverlo
            if sub_locked.expires_at > reference_time:
                return sub_locked

        # Caso B: Existe un cambio programado (R7)
        scheduled = ScheduledChange.objects.select_related("target_plan_version__plan").filter(user=user).first()
        if scheduled is not None:
            sub_locked.plan_version = scheduled.target_plan_version
            if scheduled.target_plan_version.plan.code == FREE_PLAN_CODE:
                sub_locked.expires_at = None
                sub_locked.coverage_end = None
                sub_locked.cycle_anchor_day = None
            else:
                starts_local, ends_local = sub_calendar.calculate_cycle_interval(
                    sub_locked.expires_at, sub_locked.cycle_anchor_day
                )
                sub_locked.started_at = starts_local
                sub_locked.expires_at = ends_local
                sub_locked.coverage_end = ends_local
            sub_locked.save(update_fields=[
                "plan_version", "started_at", "expires_at", "coverage_end", "cycle_anchor_day"
            ])
            scheduled.delete()
            return sub_locked

        # Caso C: Retorno automÃ¡tico a Gratis (R8)
        free_version = get_current_version(FREE_PLAN_CODE)
        sub_locked.plan_version = free_version
        sub_locked.expires_at = None
        sub_locked.coverage_end = None
        sub_locked.cycle_anchor_day = None
        sub_locked.save(update_fields=[
            "plan_version", "expires_at", "coverage_end", "cycle_anchor_day"
        ])
        return sub_locked


def get_active_subscription(user):
    sub = (
        Subscription.objects.select_related("plan_version__plan")
        .filter(user=user, status=Subscription.Status.ACTIVE)
        .first()
    )
    if sub and sub.expires_at is not None and sub.expires_at <= timezone.now():
        sub.status = Subscription.Status.EXPIRED
        sub.save(update_fields=["status"])
        return None
    return sub


def _format_iso(dt):
    if dt is None:
        return None
    return sub_calendar.to_guatemala(dt).isoformat()


def subscription_payload(sub):
    if sub is None:
        return None
    return {
        "id": sub.pk,
        "status": sub.status,
        "started_at": _format_iso(sub.started_at),
        "expires_at": _format_iso(sub.expires_at),
        "cycle_anchor_day": sub.cycle_anchor_day,
        "coverage_end": _format_iso(sub.coverage_end or sub.expires_at),
        "plan": {
            "plan_code": sub.plan_version.plan.code,
            "version_id": sub.plan_version_id,
            "name": sub.plan_version.plan.name,
            "capacity_bytes": sub.plan_version.capacity_bytes,
        },
    }


def next_cycle_payload(sub):
    if sub is None or not sub.next_cycle_starts_at:
        return None
    return {
        "starts_at": _format_iso(sub.next_cycle_starts_at),
        "ends_at": _format_iso(sub.next_cycle_ends_at),
        "plan_version_id": sub.next_cycle_plan_version_id,
    }


def scheduled_change_payload(user):
    change = ScheduledChange.objects.select_related("target_plan_version__plan").filter(user=user).first()
    if change is None:
        return None
    return {
        "id": change.pk,
        "target_plan_code": change.target_plan_version.plan.code,
        "effective_at": _format_iso(change.effective_at),
        "requires_payment": change.requires_payment,
    }


def get_allowed_actions(sub, user):
    """Calcula la lista de acciones permitidas ('contract', 'renew', 'change') para el usuario."""
    if sub is None:
        return ["contract"]
    if sub.plan_version.plan.code == FREE_PLAN_CODE:
        return ["change"]
    
    # Cobertura pagada
    actions = ["change"]
    # RenovaciÃ³n: permitida si aÃºn no tiene un ciclo futuro anticipado pagado
    if not sub.next_cycle_starts_at:
        actions.append("renew")
    return actions


def quote_payload(quote):
    return {
        "id": str(quote.id),
        "operation": quote.operation,
        "expires_at": _format_iso(quote.expires_at),
        "currency": quote.currency,
        "total": f"{quote.total:.2f}",
        "requires_payment": quote.requires_payment,
        "plan": {
            "plan_code": quote.plan_version.plan.code,
            "version_id": quote.plan_version.pk,
            "name": quote.plan_version.plan.name,
            "capacity_bytes": quote.plan_version.capacity_bytes,
        },
        "lines": quote.lines,
        "effect": quote.effect,
    }


def _validate_confirmed_free_version(version, plan_version_id):
    if version.price != 0 or (plan_version_id is not None and version.pk != plan_version_id):
        raise SubscriptionError(
            "plan_conditions_changed",
            "Las condiciones del plan cambiaron. Revisa el plan y confirma nuevamente.",
            {"plan_version_id": "La versiÃ³n confirmada no corresponde a Gratis."},
        )


@transaction.atomic
def activate_free(*, user, plan_version_id=None):
    """La API exige la versiÃ³n confirmada; llamadas internas conservan su contrato."""
    if not user.can_use_private_features:
        raise SubscriptionError(
            "account_not_eligible", "La cuenta debe estar verificada y activa para elegir un plan."
        )

    get_user_model().objects.select_for_update().get(pk=user.pk)  # serializa activaciones

    current = get_active_subscription(user)
    if current is not None:
        if current.plan_version.plan.code == FREE_PLAN_CODE:
            _validate_confirmed_free_version(current.plan_version, plan_version_id)
            return current, False  # idempotente, conserva las condiciones contratadas
        raise SubscriptionError("coverage_conflict", "Ya tienes una cobertura activa distinta a Gratis.")

    version = get_current_version(FREE_PLAN_CODE)
    _validate_confirmed_free_version(version, plan_version_id)
    subscription = Subscription.objects.create(
        user=user, plan_version=version, started_at=timezone.now(), expires_at=None
    )
    return subscription, True


def set_preference(*, user, plan_version_id):
    version = PlanVersion.objects.select_related("plan").filter(pk=plan_version_id).first()
    if version is None or not version.plan.is_available:
        raise SubscriptionError(
            "plan_unavailable",
            "El plan seleccionado no estÃ¡ disponible.",
            {"plan_version_id": "Plan no disponible."},
        )
    if version.pk != get_current_version(version.plan.code).pk:
        raise SubscriptionError(
            "plan_conditions_changed",
            "Las condiciones del plan cambiaron. Vuelve a elegirlo.",
            {"plan_version_id": "VersiÃ³n desactualizada."},
        )
    preference, _ = SubscriptionPreference.objects.update_or_create(
        user=user, defaults={"plan_version": version}
    )
    return preference  # no crea ni modifica cobertura


def get_preference(user):
    pref = SubscriptionPreference.objects.select_related("plan_version__plan").filter(user=user).first()
    if pref is None:
        return None
    version = pref.plan_version
    latest = _latest_version(version.plan) if version.plan.is_available else None
    payload = version_payload(version)
    payload["is_current"] = bool(latest and latest.pk == version.pk)
    payload["current_version_id"] = latest.pk if latest else None
    return payload


def resolve_destination(user):
    if user.role == user.Role.ADMINISTRADOR:
        return "admin"
    if get_active_subscription(user) is not None:
        return "files"
    if SubscriptionPreference.objects.filter(user=user).exists():
        return "plan_summary"
    return "plans"


# ---------------------------------------------------------------------------
# R3, R4, R5, R6, R7: MOTOR DE COTIZACIONES Y LÃ“GICA COMERCIAL
# ---------------------------------------------------------------------------

def prepare_quote(*, user, operation, plan_version_id=None):
    """
    R3 / Contrato 7.3: Emite una cotizaciÃ³n comercial temporal (15 min).
    Valida cobertura, versiones, capacidades y calcula lÃ­neas e importes exactos.
    """
    if not user.can_use_private_features:
        raise SubscriptionError(
            "account_not_eligible", "La cuenta debe estar verificada y activa para operar con planes."
        )

    current_sub = get_active_subscription(user)
    now = timezone.now()
    now_gt = sub_calendar.to_guatemala(now)
    expires_at = now + timedelta(minutes=QUOTE_TTL_MINUTES)

    if operation == Quote.Operation.CONTRACT:
        # Cuenta sin cobertura (o con Gratis)
        if current_sub is not None and current_sub.plan_version.plan.code != FREE_PLAN_CODE:
            raise SubscriptionError("coverage_conflict", "Ya tienes una cobertura pagada activa.")
        if plan_version_id is None:
            raise SubscriptionError("invalid_request", "plan_version_id es requerido para contract.")

        target_version = PlanVersion.objects.select_related("plan").filter(pk=plan_version_id).first()
        if target_version is None or not target_version.plan.is_available:
            raise SubscriptionError("plan_unavailable", "El plan seleccionado no estÃ¡ disponible.")
        latest_version = get_current_version(target_version.plan.code)
        if target_version.pk != latest_version.pk:
            raise SubscriptionError("plan_conditions_changed", "Las condiciones del plan han cambiado.")
        if target_version.price <= 0:
            raise SubscriptionError("invalid_request", "Usa activate-free para el plan Gratis.")

        starts_local, ends_local = sub_calendar.calculate_cycle_interval(now_gt)
        lines = [{
            "code": "contract_cycle",
            "description": f"Primer ciclo {target_version.plan.name}",
            "amount": f"{target_version.price:.2f}",
        }]
        effect = {
            "kind": "activate",
            "starts_at": _format_iso(starts_local),
            "ends_at": _format_iso(ends_local),
            "scheduled_change_at": None,
        }
        quote = Quote.objects.create(
            id=uuid.uuid4(),
            user=user,
            operation=Quote.Operation.CONTRACT,
            plan_version=target_version,
            currency="GTQ",
            total=target_version.price,
            requires_payment=True,
            lines=lines,
            effect=effect,
            expires_at=expires_at,
        )
        return quote

    elif operation == Quote.Operation.RENEW:
        # R5: RenovaciÃ³n manual conservando la versiÃ³n contratada
        if current_sub is None or current_sub.plan_version.plan.code == FREE_PLAN_CODE:
            raise SubscriptionError("coverage_conflict", "No tienes una suscripciÃ³n pagada que renovar.")
        if current_sub.next_cycle_starts_at is not None:
            raise SubscriptionError(
                "renewal_limit_reached",
                "Ya tienes un siguiente ciclo anticipado contratado. MÃ¡ximo 1 ciclo de renovaciÃ³n.",
            )

        # Conserva la versiÃ³n contratada originalmente, sin importar si el catÃ¡logo cambiÃ³
        contracted_version = current_sub.plan_version
        anchor_day = current_sub.cycle_anchor_day or current_sub.started_at.day
        cycle_start = current_sub.expires_at
        _, cycle_end = sub_calendar.calculate_cycle_interval(cycle_start, anchor_day)

        lines = [{
            "code": "renewal_cycle",
            "description": f"RenovaciÃ³n ciclo {contracted_version.plan.name}",
            "amount": f"{contracted_version.price:.2f}",
        }]
        effect = {
            "kind": "renew",
            "starts_at": _format_iso(cycle_start),
            "ends_at": _format_iso(cycle_end),
            "scheduled_change_at": None,
        }
        quote = Quote.objects.create(
            id=uuid.uuid4(),
            user=user,
            operation=Quote.Operation.RENEW,
            plan_version=contracted_version,
            currency="GTQ",
            total=contracted_version.price,
            requires_payment=True,
            lines=lines,
            effect=effect,
            expires_at=expires_at,
        )
        return quote

    elif operation == Quote.Operation.CHANGE:
        # R6 / R7: Cambio de plan (Upgrade o Downgrade)
        if plan_version_id is None:
            raise SubscriptionError("invalid_request", "plan_version_id es requerido para change.")

        target_version = PlanVersion.objects.select_related("plan").filter(pk=plan_version_id).first()
        if target_version is None or not target_version.plan.is_available:
            raise SubscriptionError("plan_unavailable", "El plan seleccionado no estÃ¡ disponible.")
        latest_version = get_current_version(target_version.plan.code)
        if target_version.pk != latest_version.pk:
            raise SubscriptionError("plan_conditions_changed", "Las condiciones del plan han cambiado.")

        # Si el usuario estÃ¡ en Gratis, un cambio a pagado es un contrato inicial
        if current_sub is None or current_sub.plan_version.plan.code == FREE_PLAN_CODE:
            if target_version.plan.code == FREE_PLAN_CODE:
                raise SubscriptionError("coverage_conflict", "Ya te encuentras en el plan Gratis.")
            return prepare_quote(user=user, operation=Quote.Operation.CONTRACT, plan_version_id=plan_version_id)

        # Si ya tiene contratado el mismo plan actual
        current_version = current_sub.plan_version
        if target_version.plan.code == current_version.plan.code:
            raise SubscriptionError("coverage_conflict", "Ya tienes contratado este plan.")

        from files.services import get_used_bytes
        used_bytes = get_used_bytes(user)

        # Determinar si es UPGRADE o DOWNGRADE por precio o capacidad
        is_upgrade = target_version.price > current_version.price

        if is_upgrade:
            # R6: Mejora inmediata (BÃ¡sico a Premium)
            # 1. Ajuste proporcional del ciclo actual
            cycle_start = current_sub.started_at
            cycle_end = current_sub.expires_at
            current_adj = calculate_upgrade_proration(
                now=now,
                cycle_start=cycle_start,
                cycle_end=cycle_end,
                current_price=current_version.price,
                target_price=target_version.price,
            )

            lines = [{
                "code": "current_cycle_adjustment",
                "description": f"Ajuste proporcional ciclo actual a {target_version.plan.name}",
                "amount": f"{current_adj:.2f}",
            }]
            total = current_adj

            # 2. Si ya pagÃ³ el siguiente ciclo anticipado, cobrar la diferencia completa de ese ciclo
            if current_sub.next_cycle_starts_at is not None:
                next_diff = round_money(target_version.price - current_version.price)
                lines.append({
                    "code": "next_cycle_adjustment",
                    "description": f"Diferencia ciclo anticipado a {target_version.plan.name}",
                    "amount": f"{next_diff:.2f}",
                })
                total += next_diff

            effect = {
                "kind": "upgrade",
                "starts_at": _format_iso(now),
                "ends_at": _format_iso(current_sub.expires_at),
                "scheduled_change_at": None,
            }
            quote = Quote.objects.create(
                id=uuid.uuid4(),
                user=user,
                operation=Quote.Operation.CHANGE,
                plan_version=target_version,
                currency="GTQ",
                total=total,
                # Contrato 7.4: Una mejora con importe 0.00 sigue requiriendo pago en el simulador
                requires_payment=True,
                lines=lines,
                effect=effect,
                expires_at=expires_at,
            )
            return quote

        else:
            # R7: Bajada programada al terminar cobertura pagada (o retorno a Gratis)
            # Comprobar capacidad contra consumo actual
            if used_bytes > target_version.capacity_bytes:
                raise SubscriptionError(
                    "quota_exceeded",
                    f"Tu consumo actual ({used_bytes} bytes) supera la capacidad del plan destino ({target_version.capacity_bytes} bytes).",
                )

            # Efecto: programar al vencer el fin de cobertura total
            coverage_end = current_sub.coverage_end or current_sub.expires_at
            kind = "schedule_free" if target_version.plan.code == FREE_PLAN_CODE else "schedule_downgrade"

            lines = [{
                "code": "schedule_change",
                "description": f"ProgramaciÃ³n cambio a {target_version.plan.name} al terminar cobertura",
                "amount": "0.00",
            }]
            effect = {
                "kind": kind,
                "starts_at": _format_iso(coverage_end),
                "ends_at": None if target_version.plan.code == FREE_PLAN_CODE else _format_iso(
                    sub_calendar.add_calendar_months(coverage_end, 1, current_sub.cycle_anchor_day)
                ),
                "scheduled_change_at": _format_iso(coverage_end),
            }
            quote = Quote.objects.create(
                id=uuid.uuid4(),
                user=user,
                operation=Quote.Operation.CHANGE,
                plan_version=target_version,
                currency="GTQ",
                total=Decimal("0.00"),
                requires_payment=False,
                lines=lines,
                effect=effect,
                expires_at=expires_at,
            )
            return quote

    else:
        raise SubscriptionError("invalid_request", f"OperaciÃ³n '{operation}' no soportada.")


def get_quote(*, user, quote_id):
    """Contrato 7.3: Devuelve la cotizaciÃ³n si pertenece al usuario y no ha expirado."""
    quote = Quote.objects.select_related("plan_version__plan").filter(pk=quote_id, user=user).first()
    if quote is None:
        raise SubscriptionError("not_found", "CotizaciÃ³n no encontrada.")
    if timezone.now() > quote.expires_at:
        quote.status = Quote.Status.EXPIRED
        quote.save(update_fields=["status"])
        raise SubscriptionError("quote_expired", "La cotizaciÃ³n ha expirado. Solicita una nueva.")
    return quote


def validate_quote_for_execution(*, user, quote_id):
    """
    R3 / Contrato 7.3 y 7.6:
    Valida la cotización bajo bloqueo antes del cobro en payments.
    Verifica propiedad, vigencia, estado y que las condiciones comerciales no hayan cambiado.
    Devuelve un Mapping (dict) con los campos públicos requeridos por payments.
    """
    # 1. Bloqueo de la cotización
    quote = (
        Quote.objects.select_for_update()
        .select_related("plan_version__plan")
        .filter(pk=quote_id, user=user)
        .first()
    )
    if quote is None:
        raise SubscriptionError("not_found", "Cotización no encontrada.")

    if quote.status != Quote.Status.PENDING:
        if quote.status == Quote.Status.EXECUTED:
            raise SubscriptionError("quote_already_processed", "Esta cotización ya fue ejecutada.")
        raise SubscriptionError("quote_expired", "La cotización ya no está disponible.")

    now = timezone.now()
    if now > quote.expires_at:
        quote.status = Quote.Status.EXPIRED
        quote.save(update_fields=["status"])
        raise SubscriptionError("quote_expired", "La cotización ha expirado. Solicita una nueva.")

    # 2. Revalidar condiciones del catálogo
    target_plan = quote.plan_version.plan
    if not target_plan.is_available:
        raise SubscriptionError("plan_unavailable", "El plan seleccionado ya no está disponible.")

    # En contrataciones y cambios, revalidar que la versión siga siendo la vigente en el catálogo
    if quote.operation in (Quote.Operation.CONTRACT, Quote.Operation.CHANGE):
        current_catalog_version = get_current_version(target_plan.code)
        if quote.plan_version_id != current_catalog_version.pk:
            raise SubscriptionError("plan_conditions_changed", "Las condiciones del plan han cambiado.")

    # 3. Bloqueo y revalidación de la suscripción actual del usuario
    current_sub = (
        Subscription.objects.select_for_update()
        .select_related("plan_version__plan")
        .filter(user=user, status=Subscription.Status.ACTIVE)
        .first()
    )

    if quote.operation == Quote.Operation.CONTRACT:
        if current_sub is not None and current_sub.plan_version.plan.code != FREE_PLAN_CODE:
            raise SubscriptionError("coverage_conflict", "Ya existe una cobertura pagada activa.")

    elif quote.operation == Quote.Operation.RENEW:
        if current_sub is None or current_sub.plan_version.plan.code == FREE_PLAN_CODE:
            raise SubscriptionError("coverage_conflict", "No hay una suscripción activa para renovar.")
        if current_sub.next_cycle_starts_at is not None:
            raise SubscriptionError("renewal_limit_reached", "Ya existe un siguiente ciclo contratado.")
        # La versión contratada original debe coincidir
        if current_sub.plan_version_id != quote.plan_version_id:
            raise SubscriptionError("plan_conditions_changed", "La versión de suscripción no coincide.")

    elif quote.operation == Quote.Operation.CHANGE:
        if current_sub is None or current_sub.plan_version.plan.code == FREE_PLAN_CODE:
            pass  # de gratis a pagado es contrato
        else:
            if current_sub.plan_version.plan.code == quote.plan_version.plan.code:
                raise SubscriptionError("coverage_conflict", "Ya tienes contratado este plan.")
            from files.services import get_used_bytes
            used_bytes = get_used_bytes(user)
            if used_bytes > quote.plan_version.capacity_bytes:
                raise SubscriptionError("quota_exceeded", "El consumo actual supera la capacidad del plan destino.")

    return quote_payload(quote)


def apply_approved_quote(*, user, quote, payment, approved_at=None):
    """
    R2, R5, R6 / Contrato 7.6:
    Aplica los derechos comerciales de una cotización aprobada.
    Participa dentro de la transacción de checkout de Daniela.
    Devuelve la instancia de Subscription resultante.
    """
    approval_time = approved_at or timezone.now()
    quote_id = quote["id"]
    quote_obj = Quote.objects.select_for_update().get(pk=quote_id)

    target_version = quote_obj.plan_version
    anchor_day = sub_calendar.to_guatemala(approval_time).day

    current_sub = (
        Subscription.objects.select_for_update()
        .select_related("plan_version__plan")
        .filter(user=user, status=Subscription.Status.ACTIVE)
        .first()
    )

    if quote_obj.operation == Quote.Operation.CONTRACT:
        # Inicio inmediato de ciclo desde aprobación
        starts_local, ends_local = sub_calendar.calculate_cycle_interval(approval_time, anchor_day)
        if current_sub is not None:
            # Reutilizar registro de suscripción existente (evolución de identidad única)
            current_sub.plan_version = target_version
            current_sub.started_at = starts_local
            current_sub.expires_at = ends_local
            current_sub.cycle_anchor_day = anchor_day
            current_sub.coverage_end = ends_local
            current_sub.next_cycle_starts_at = None
            current_sub.next_cycle_ends_at = None
            current_sub.next_cycle_plan_version = None
            current_sub.save()
            sub_result = current_sub
        else:
            sub_result = Subscription.objects.create(
                user=user,
                plan_version=target_version,
                started_at=starts_local,
                expires_at=ends_local,
                cycle_anchor_day=anchor_day,
                coverage_end=ends_local,
            )

    elif quote_obj.operation == Quote.Operation.RENEW:
        # R5: Agrega exactamente un siguiente ciclo anticipado pagado
        anchor = current_sub.cycle_anchor_day or current_sub.started_at.day
        cycle_start = current_sub.expires_at
        _, cycle_end = sub_calendar.calculate_cycle_interval(cycle_start, anchor)

        current_sub.next_cycle_starts_at = cycle_start
        current_sub.next_cycle_ends_at = cycle_end
        current_sub.next_cycle_plan_version = target_version
        current_sub.coverage_end = cycle_end
        current_sub.save(update_fields=[
            "next_cycle_starts_at", "next_cycle_ends_at", "next_cycle_plan_version", "coverage_end"
        ])
        sub_result = current_sub

    elif quote_obj.operation == Quote.Operation.CHANGE:
        # R6: Mejora inmediata
        current_sub.plan_version = target_version
        if current_sub.next_cycle_plan_version_id is not None:
            current_sub.next_cycle_plan_version = target_version
        current_sub.save(update_fields=["plan_version", "next_cycle_plan_version"])
        sub_result = current_sub

    else:
        raise SubscriptionError("invalid_request", f"Operación '{quote_obj.operation}' no válida para pago.")

    quote_obj.status = Quote.Status.EXECUTED
    quote_obj.save(update_fields=["status"])
    return sub_result


def confirm_scheduled_quote(*, user, quote_id, operation_key=None):
    """
    Contrato 7.4:
    Confirma una cotización diferida (schedule_downgrade o schedule_free).
    Solo acepta cotizaciones con requires_payment=False.
    Crea o actualiza ScheduledChange sin activar anticipadamente ni cobrar.
    """
    quote = get_quote(user=user, quote_id=quote_id)
    if quote.requires_payment:
        raise SubscriptionError("invalid_request", "Esta cotización requiere pago. Usa checkout.")

    current_sub = get_active_subscription(user)
    if current_sub is None:
        raise SubscriptionError("coverage_conflict", "No tienes una suscripción activa.")

    from files.services import get_used_bytes
    used_bytes = get_used_bytes(user)
    if used_bytes > quote.plan_version.capacity_bytes:
        raise SubscriptionError(
            "quota_exceeded",
            f"Tu consumo ({used_bytes} bytes) excede la capacidad del plan destino ({quote.plan_version.capacity_bytes} bytes).",
        )

    coverage_end = current_sub.coverage_end or current_sub.expires_at
    scheduled, _ = ScheduledChange.objects.update_or_create(
        user=user,
        defaults={
            "subscription": current_sub,
            "target_plan_version": quote.plan_version,
            "effective_at": coverage_end,
            "requires_payment": False,
        },
    )
    quote.status = Quote.Status.CONFIRMED
    quote.save(update_fields=["status"])
    return scheduled, current_sub


def cancel_scheduled_change(*, user):
    """
    Contrato 7.4:
    Cancela la programación pendiente del propietario. Idempotente.
    """
    ScheduledChange.objects.filter(user=user).delete()