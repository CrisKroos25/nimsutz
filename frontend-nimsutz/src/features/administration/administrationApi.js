import { apiRequest } from '@shared/api/httpClient';

const queryString = (values) => {
    const query = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => { if (value) query.set(key, value); });
    const encoded = query.toString();
    return encoded ? `?${encoded}` : '';
};

export const getMetrics = (filters) => apiRequest(`/api/administration/metrics/${queryString(filters)}`);
export const listAdministrationPayments = (filters, page = 1) =>
    apiRequest(`/api/administration/payments/${queryString({ ...filters, page, page_size: 20 })}`);
export const getAdministrationPayment = (id) =>
    apiRequest(`/api/administration/payments/${encodeURIComponent(id)}/`);
