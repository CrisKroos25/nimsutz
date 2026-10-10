import { apiRequest } from './httpClient.js';

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const registerAccount = (values) => apiRequest('/api/auth/register/', json('POST', values));
// El contrato del servidor se adapta aquí para mantener estables las pantallas.
const PLAN_CODES = { free: 'gratis', basic: 'basico', premium: 'premium' };

function normalizePlan(plan) {
    return { ...plan, code: PLAN_CODES[plan?.plan_code] || plan?.plan_code,
        available: plan?.contractable,
        period: plan?.duration_days ? `${plan.duration_days} días` : null };
}

export async function getPlans() {
    const data = await apiRequest('/api/plans/');
    const plans = Array.isArray(data?.plans) ? data.plans.map(normalizePlan) : null;
    if (!plans || plans.some((plan) =>
        !plan || !plan.version_id || typeof plan.code !== 'string' || typeof plan.name !== 'string' ||
        !Number.isFinite(Number(plan.price)) || Number(plan.price) < 0 || typeof plan.currency !== 'string' ||
        !Number.isFinite(plan.capacity_bytes) || plan.capacity_bytes <= 0 || typeof plan.available !== 'boolean')) {
        throw new Error('No se pudieron confirmar las condiciones de los planes. Inténtalo más tarde.');
    }
    return plans;
}
export async function getPreference() {
    const data = await apiRequest('/api/subscriptions/preference/');
    if (!data || !Object.hasOwn(data, 'preference') ||
        (data.preference !== null && (!data.preference?.version_id || typeof data.preference.is_current !== 'boolean'))) {
        throw new Error('No se pudo consultar tu selección de plan.');
    }
    return { preferred_plan_version_id: data.preference?.version_id ?? null,
        is_current: data.preference?.is_current ?? true };
}
export const setPreference = (versionId) => apiRequest('/api/subscriptions/preference/', json('PUT', { plan_version_id: versionId }));
export const getSubscription = () => apiRequest('/api/subscriptions/current/');
export const activateFree = (versionId) => apiRequest('/api/subscriptions/activate-free/', json('POST', { plan_version_id: versionId }));
export async function getAccountOverview() {
    const data = await apiRequest('/api/account/overview/');
    // Ausencia de coverage no equivale a una respuesta explícita sin plan.
    const subscription = validateSubscription({ subscription: data?.coverage });
    return { ...data, subscription, storage: data.usage };
}

export async function withAccountDestination(session) {
    if (!session.user || session.user.role === 'administrador') return session;
    try {
        const overview = await getAccountOverview();
        if (!['files', 'plans', 'plan_summary'].includes(overview.destination)) {
            throw new Error('No se pudo confirmar el acceso de tu cuenta.');
        }
        return { ...session, destination: overview.destination };
    } catch {
        // La identidad ya fue autenticada. Un fallo de cobertura no cierra la sesión
        // ni concede acceso: RequireSession muestra el error y permite reintentar.
        return { ...session, destination: 'plans',
            accessError: 'Tu sesión está iniciada, pero no pudimos consultar tu plan. Reintenta la consulta.' };
    }
}

export function serviceMessage(error, subject) {
    if ([404, 405, 501, 503].includes(error.status)) return `${subject} no está disponible por el momento. Inténtalo más tarde.`;
    return error.message || 'No se pudo conectar. Inténtalo de nuevo.';
}

// Un contrato incompleto nunca se interpreta como una cuenta sin cobertura.
export function validateSubscription(data) {
    if (!data || !Object.hasOwn(data, 'subscription') ||
        (data.subscription !== null && (typeof data.subscription !== 'object' ||
            typeof data.subscription.plan?.name !== 'string' || !data.subscription.plan.name.trim()))) {
        throw new Error('No se pudo confirmar el estado de tu suscripción. Inténtalo más tarde.');
    }
    return data.subscription;
}


export async function selectPlan(versionId) {
    try {
        await setPreference(versionId);
        return { needsReselection: false };
    } catch (error) {
        if (!['plan_conditions_changed', 'plan_unavailable'].includes(error.code)) throw error;
        // Actualizar no equivale a aceptar las nuevas condiciones: el usuario elige otra vez.
        return { needsReselection: true, plans: await getPlans() };
    }
}
