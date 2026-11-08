// Reglas puras de la pantalla de auditoría (M21): etiquetas, filtros y metadata segura.
export const AUDIT_PAGE_SIZE = 20;

export const ACTION_LABELS = {
    'client.suspended': 'Cliente suspendido',
    'client.reactivated': 'Cliente reactivado',
    'plan.version_published': 'Versión de plan publicada',
    'plan.deactivated': 'Plan desactivado',
    'administration.access_denied': 'Acceso denegado a administración',
};

export const RESULT_LABELS = {
    success: 'Exitoso',
    rejected: 'Rechazado',
    no_change: 'Sin cambios',
    error: 'Error',
};

export const RESULT_TONES = { success: 'success', rejected: 'danger', no_change: 'neutral', error: 'danger' };

export const ENTITY_LABELS = { client: 'Cliente', plan: 'Plan', administration: 'Administración' };

// Solo se muestran las claves del contrato; cualquier otra se ignora.
export const METADATA_LABELS = {
    previous_status: 'Estado anterior',
    new_status: 'Estado nuevo',
    previous_version_id: 'Versión anterior',
    new_version_id: 'Versión nueva',
    previous_active: 'Activo antes',
    new_active: 'Activo después',
    reason_code: 'Motivo',
};

export const EMPTY_AUDIT_FILTERS = {
    action: '', entity_type: '', entity_id: '', result: '', actor_id: '', date_from: '', date_to: '',
};

export const hasActiveAuditFilters = (filters) => Object.values(filters).some(Boolean);

export function validateAuditFilters(filters) {
    const errors = {};
    if (filters.actor_id && !/^[1-9]\d*$/.test(filters.actor_id)) errors.actor_id = 'Usa un número de administrador válido.';
    if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
        errors.date_to = 'La fecha final no puede ser anterior a la inicial.';
    }
    return errors;
}

export function buildAuditQuery(filters, page = 1) {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, String(value).trim()); });
    query.set('page', String(page));
    query.set('page_size', String(AUDIT_PAGE_SIZE));
    return `?${query.toString()}`;
}

export const auditTotalPages = (count) => Math.max(1, Math.ceil(count / AUDIT_PAGE_SIZE));

export const actionLabel = (code) => ACTION_LABELS[code] || 'Acción no reconocida';
export const resultLabel = (code) => RESULT_LABELS[code] || 'Resultado no reconocido';
export const entityLabel = (type) => ENTITY_LABELS[type] || type || '—';

export function actorLabel(actor) {
    if (!actor) return 'Sistema o cuenta eliminada';
    return actor.label || (actor.id ? `Usuario ${actor.id}` : 'Sistema o cuenta eliminada');
}

function metadataValue(value) {
    if (value === null || value === undefined || value === '') return '—';
    if (value === true) return 'Sí';
    if (value === false) return 'No';
    return String(value);
}

export function metadataRows(metadata) {
    return Object.entries(METADATA_LABELS)
        .filter(([key]) => metadata && Object.prototype.hasOwnProperty.call(metadata, key))
        .map(([key, label]) => ({ key, label, value: metadataValue(metadata[key]) }));
}

export function validateAuditPage(data) {
    const valid = data && Array.isArray(data.results) && Number.isInteger(data.count);
    if (!valid) throw new Error('La respuesta de auditoría no tiene el formato esperado.');
    return data;
}

export function auditErrorMessage(error) {
    if (error?.status === 403) return 'No tienes permiso para consultar la auditoría.';
    if (error?.status === 404) return 'Esa página o evento de auditoría ya no existe.';
    return error?.message || 'No se pudo consultar la auditoría. Intenta de nuevo.';
}
