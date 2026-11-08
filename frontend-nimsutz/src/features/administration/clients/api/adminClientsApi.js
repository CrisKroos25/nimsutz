// AJUSTAR la ruta del import al apiRequest real del proyecto.
// Se asume: apiRequest(url, { method, body, signal }) -> JSON, y lanza un error con .status si la respuesta no es 2xx.
// apiRequest ya se encarga de la sesión y del CSRF.
import { apiRequest } from '@shared/api/httpClient';

const BASE = '/api/administration/clients/';

export function fetchClients({ search, status, planCode, page }, { signal } = {}) {
    const query = new URLSearchParams();
    if (search) query.set('search', search);
    if (status) query.set('status', status);
    if (planCode) query.set('plan_code', planCode);
    if (page > 1) query.set('page', String(page));
    const qs = query.toString();
    return apiRequest(`${BASE}${qs ? `?${qs}` : ''}`, { signal });
}

export function fetchClient(clientId, { signal } = {}) {
    return apiRequest(`${BASE}${clientId}/`, { signal });
}

export function suspendClient(clientId) {
    return apiRequest(`${BASE}${clientId}/suspend/`, { method: 'POST'});
}

export function reactivateClient(clientId) {
    return apiRequest(`${BASE}${clientId}/reactivate/`, { method: 'POST'});
}