import { apiRequest } from '@shared/api/httpClient';
import { buildAuditQuery, validateAuditPage } from './auditModel';

export const listAuditEvents = async (filters, page = 1) =>
    validateAuditPage(await apiRequest(`/api/administration/audit/${buildAuditQuery(filters, page)}`));

export const getAuditEvent = (id) => apiRequest(`/api/administration/audit/${encodeURIComponent(id)}/`);
