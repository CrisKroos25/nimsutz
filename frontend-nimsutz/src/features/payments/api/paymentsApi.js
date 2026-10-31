import { apiRequest } from '../../../shared/api/httpClient';

export const getQuote = (quoteId) => apiRequest(`/api/subscriptions/quotes/${quoteId}/`);
export const getPaymentResult = (paymentId) => apiRequest(`/api/payments/results/${paymentId}/`);
export const getOperationResult = (key) => apiRequest(`/api/payments/operations/${key}/`);
export const checkout = (key, body) => apiRequest('/api/payments/checkout/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key },
    body: JSON.stringify(body),
});
