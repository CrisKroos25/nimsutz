import { apiRequest } from './httpClient.js';

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const registerAccount = (values) => apiRequest('/api/auth/register/', json('POST', values));
export async function getPlans() {
    const data = await apiRequest('/api/plans/');
    if (!Array.isArray(data?.plans) || data.plans.some((plan) =>
        !plan || !plan.version_id || typeof plan.code !== 'string' || typeof plan.name !== 'string' ||
        !Number.isFinite(Number(plan.price)) || Number(plan.price) < 0 || typeof plan.currency !== 'string' ||
        !Number.isFinite(plan.capacity_bytes) || plan.capacity_bytes <= 0 || typeof plan.available !== 'boolean')) {
        throw new Error('No se pudieron confirmar las condiciones de los planes. Inténtalo más tarde.');
    }
    return data.plans;
}
export const getPreference = () => apiRequest('/api/subscriptions/preference/');
export const setPreference = (versionId) => apiRequest('/api/subscriptions/preference/', json('PUT', { preferred_plan_version_id: versionId }));
export const getSubscription = () => apiRequest('/api/subscriptions/current/');
export const activateFree = (versionId) => apiRequest('/api/subscriptions/activate-free/', json('POST', { plan_version_id: versionId }));
export const getAccountOverview = () => apiRequest('/api/account/overview/');

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
