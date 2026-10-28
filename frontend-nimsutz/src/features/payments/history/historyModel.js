// Lógica pura del historial de pagos (sin React) para poder probarla con node:test.
export const PAGE_SIZE = 20;

export const STATUS_LABELS = { approved: 'Aprobado', rejected: 'Rechazado' };
export const OPERATION_LABELS = { contract: 'Contratación', renew: 'Renovación', change: 'Cambio de plan' };
export const REASON_LABELS = {
    card_not_found: 'Tarjeta no encontrada',
    card_details_invalid: 'Datos de la tarjeta no coinciden',
    card_disabled: 'Tarjeta deshabilitada',
    card_expired: 'Tarjeta vencida',
    currency_mismatch: 'Moneda no compatible',
    insufficient_funds: 'Saldo insuficiente',
};
export const EMPTY_FILTERS = { status: '', operation: '', date_from: '', date_to: '' };

const MONEY = /^\d+\.\d{2}$/;

export const hasActiveFilters = (filters) => Object.values(filters).some(Boolean);

// El servidor es quien filtra: aquí solo se arma la consulta con lo que el usuario eligió.
export function buildHistoryQuery(filters, page = 1) {
    const params = new URLSearchParams();
    for (const key of Object.keys(EMPTY_FILTERS)) if (filters[key]) params.set(key, filters[key]);
    if (page > 1) params.set('page', String(page));
    params.set('page_size', String(PAGE_SIZE));
    return `?${params}`;
}

// Mensajes locales para no ir al servidor con un rango imposible.
export function validateFilters(filters) {
    const errors = {};
    if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
        errors.date_to = 'La fecha final no puede ser anterior a la inicial.';
    }
    return errors;
}

export const totalPages = (count) => Math.max(1, Math.ceil(count / PAGE_SIZE));

export const maskedCard = (last4) => (/^\d{4}$/.test(last4 || '') ? `•••• ${last4}` : 'No disponible');

export const reasonText = (code) => REASON_LABELS[code] || 'Motivo no disponible';

const fail = () => { throw new Error('No se pudo interpretar la respuesta del historial. Inténtalo más tarde.'); };

export function validatePayment(payment) {
    if (!payment || !Number.isInteger(payment.id) || !(payment.status in STATUS_LABELS) ||
        !(payment.operation in OPERATION_LABELS) || typeof payment.amount !== 'string' ||
        !MONEY.test(payment.amount) || typeof payment.currency !== 'string' ||
        typeof payment.reference !== 'string' || Number.isNaN(Date.parse(payment.created_at))) fail();
    return payment;
}

export function validateHistoryPage(data) {
    if (!data || !Number.isInteger(data.count) || data.count < 0 || !Array.isArray(data.results)) fail();
    data.results.forEach(validatePayment);
    return data;
}

export function validatePaymentDetail(data) {
    validatePayment(data);
    if (!Array.isArray(data.lines) || data.lines.some((line) =>
        typeof line?.code !== 'string' || typeof line.description !== 'string' || !MONEY.test(line.amount))) fail();
    if (!data.plan || typeof data.plan !== 'object') fail();
    return data;
}

export function formatDateTime(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleString('es-GT', { timeZone: 'America/Guatemala', dateStyle: 'medium', timeStyle: 'short' });
}

export function historyErrorMessage(error) {
    if (error?.status === 403) return 'Tu cuenta no puede consultar pagos en este momento.';
    if (error?.status === 404) return 'No encontramos este pago entre los de tu cuenta.';
    return error?.message || 'No se pudo consultar el historial. Inténtalo de nuevo.';
}
