import { apiRequest } from '../../shared/api/httpClient.js';
import { validateCurrent, validateQuote } from './subscriptionModel.js';

const json = (method, body, headers = {}) => ({
    method, headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body),
});

export async function getCurrentSubscription() {
    return validateCurrent(await apiRequest('/api/subscriptions/current/'));
}

// Solo se envía la operación y, si aplica, la versión elegida: el importe lo calcula el servidor.
export async function createQuote(operation, planVersionId) {
    const body = operation === 'renew' ? { operation } : { operation, plan_version_id: planVersionId };
    return validateQuote(await apiRequest('/api/subscriptions/quotes/', json('POST', body)));
}

export const confirmScheduledQuote = (quoteId, operationKey) => apiRequest(
    `/api/subscriptions/quotes/${encodeURIComponent(quoteId)}/confirm/`,
    json('POST', {}, { 'Idempotency-Key': operationKey }),
);

export const cancelScheduledChange = () => apiRequest('/api/subscriptions/scheduled-change/', { method: 'DELETE' });
