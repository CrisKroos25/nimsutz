import { apiRequest } from '@shared/api/httpClient';

/**
 * Cliente API para el Catálogo Administrativo Versionado (M19 - Rodrigo).
 */

export function formatCapacity(bytes) {
    if (!bytes && bytes !== 0) return '0 B';
    const num = Number(bytes);
    const MB = 1024 * 1024;
    const GB = 1024 * 1024 * 1024;

    if (num >= GB) {
        const val = num / GB;
        return `${Number.isInteger(val) ? val : val.toFixed(1)} GB`;
    }
    const val = num / MB;
    return `${Number.isInteger(val) ? val : val.toFixed(0)} MB`;
}

export function parseCapacityToBytes(value, unit) {
    const num = parseFloat(value);
    if (isNaN(num) || num <= 0) return 0;
    const MB = 1024 * 1024;
    const GB = 1024 * 1024 * 1024;
    return Math.round(num * (unit === 'GB' ? GB : MB));
}

export async function fetchAdminPlans({ active = null, page = 1, pageSize = 20 } = {}) {
    const params = new URLSearchParams();
    if (active !== null) {
        params.set('active', active ? 'true' : 'false');
    }
    if (page > 1) {
        params.set('page', String(page));
    }
    if (pageSize !== 20) {
        params.set('page_size', String(pageSize));
    }

    const query = params.toString() ? `?${params.toString()}` : '';
    return await apiRequest(`/api/administration/plans/${query}`);
}

export async function fetchPlanVersions(planId, { page = 1, pageSize = 20 } = {}) {
    const params = new URLSearchParams();
    if (page > 1) params.set('page', String(page));
    if (pageSize !== 20) params.set('page_size', String(pageSize));

    const query = params.toString() ? `?${params.toString()}` : '';
    return await apiRequest(`/api/administration/plans/${planId}/versions/${query}`);
}

export async function publishPlanVersion(planId, payload) {
    return await apiRequest(`/api/administration/plans/${planId}/versions/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });
}

export async function deactivatePlan(planId) {
    return await apiRequest(`/api/administration/plans/${planId}/deactivate/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
    });
}
