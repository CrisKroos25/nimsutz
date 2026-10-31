import { apiRequest } from '../../../shared/api/httpClient.js';
import { buildHistoryQuery, validateHistoryPage, validatePaymentDetail } from './historyModel.js';

export async function listPayments(filters, page = 1) {
    return validateHistoryPage(await apiRequest(`/api/payments/${buildHistoryQuery(filters, page)}`));
}

export async function getPaymentDetail(paymentId) {
    return validatePaymentDetail(await apiRequest(`/api/payments/${encodeURIComponent(paymentId)}/`));
}
