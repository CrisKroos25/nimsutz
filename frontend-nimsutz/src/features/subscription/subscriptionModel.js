// Lógica pura de las pantallas de suscripción. No calcula importes ni fechas: todo viene del servidor.
import { validateSubscription } from '../../shared/api/accountApi.js';

export const FREE_CODE = 'free';
const ACTIONS = ['contract', 'renew', 'change'];
const OPERATIONS = ['contract', 'renew', 'change'];
const EFFECTS = ['activate', 'renew', 'upgrade', 'schedule_downgrade', 'schedule_free'];
const MONEY = /^\d+\.\d{2}$/;

export const EFFECT_LABELS = {
    activate: 'Tu plan se activa cuando el pago sea aprobado.',
    renew: 'Tu cobertura se extiende un ciclo más cuando el pago sea aprobado.',
    upgrade: 'La mejora se aplica de inmediato cuando el pago sea aprobado.',
    schedule_downgrade: 'Al terminar tu cobertura podrás confirmar y pagar el plan destino. No se cobra ahora ni automáticamente.',
    schedule_free: 'Volverás a Gratis cuando termine tu cobertura actual. No se cobra ahora y no pierdes archivos.',
};

const fail = (message) => { throw new Error(message); };

export function validateCurrent(data) {
    const subscription = validateSubscription(data);
    const bad = !Array.isArray(data.allowed_actions) || data.allowed_actions.some((code) => !ACTIONS.includes(code)) ||
        (data.next_cycle != null && typeof data.next_cycle !== 'object') ||
        (data.scheduled_change != null && (typeof data.scheduled_change !== 'object' || !data.scheduled_change.effective_at));
    if (bad) fail('No se pudo confirmar tu suscripción. Inténtalo más tarde.');
    return {
        subscription,
        nextCycle: data.next_cycle || null,
        scheduledChange: data.scheduled_change || null,
        allowed: data.allowed_actions,
    };
}

export function validateQuote(data) {
    const quote = data?.quote;
    const bad = !quote || typeof quote.id !== 'string' || !OPERATIONS.includes(quote.operation) ||
        typeof quote.currency !== 'string' || !MONEY.test(quote.total) || typeof quote.requires_payment !== 'boolean' ||
        typeof quote.plan?.name !== 'string' || Number.isNaN(Date.parse(quote.expires_at)) ||
        !Array.isArray(quote.lines) || quote.lines.some((line) => typeof line?.description !== 'string' || !MONEY.test(line.amount)) ||
        !EFFECTS.includes(quote.effect?.kind);
    if (bad) fail('No se pudo interpretar el resumen. Inténtalo de nuevo.');
    return quote;
}

export const isFree = (subscription) => subscription?.plan?.plan_code === FREE_CODE;

// Gratis no vence ni se renueva; un plan pagado muestra el fin de su cobertura.
export function coverageEnd(subscription) {
    if (!subscription || isFree(subscription)) return null;
    return subscription.coverage_end || subscription.expires_at || null;
}

// Qué sigue después de ver un resumen: pagar, confirmar un cambio sin cobro, o nada.
export function nextStep(quote) {
    if (quote.requires_payment) return 'checkout';
    if (['schedule_downgrade', 'schedule_free'].includes(quote.effect.kind)) return 'confirm';
    return 'none';
}

export const isExpired = (quote, now = Date.now()) => Date.parse(quote.expires_at) <= now;

// Planes a los que se puede cambiar: nunca el actual; los no contratables se muestran deshabilitados.
export function changeTargets(plans, subscription) {
    return plans
        .filter((plan) => plan.version_id !== subscription?.plan?.version_id &&
            plan.plan_code !== subscription?.plan?.plan_code)
        .map((plan) => ({ plan, selectable: plan.available === true }));
}

export function quotaState(usage) {
    if (!usage || !Number.isFinite(usage.used_bytes) || !Number.isFinite(usage.capacity_bytes)) return null;
    const exceeded = usage.used_bytes > usage.capacity_bytes;
    const percent = usage.capacity_bytes > 0 ? Math.round((usage.used_bytes / usage.capacity_bytes) * 100) : 0;
    return { exceeded, percent, available: Math.max(0, usage.capacity_bytes - usage.used_bytes) };
}

export function quoteErrorMessage(error) {
    const byCode = {
        renewal_limit_reached: 'Ya tienes un ciclo siguiente pagado. No se puede renovar más por ahora.',
        plan_conditions_changed: 'Las condiciones del plan cambiaron. Revisa el resumen nuevo antes de continuar.',
        plan_unavailable: 'Este plan no está disponible por el momento.',
        quota_exceeded: error?.message,
        quote_expired: 'El resumen venció. Genera uno nuevo.',
        coverage_conflict: 'Tu cobertura cambió. Vuelve a consultar tu suscripción.',
        account_not_eligible: 'Tu cuenta no puede realizar esta operación en este momento.',
    };
    return byCode[error?.code] || error?.message || 'No se pudo completar la operación. Inténtalo de nuevo.';
}

export const newOperationKey = () => globalThis.crypto.randomUUID();

export function formatDay(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleDateString('es-GT', { timeZone: 'America/Guatemala', dateStyle: 'long' });
}
