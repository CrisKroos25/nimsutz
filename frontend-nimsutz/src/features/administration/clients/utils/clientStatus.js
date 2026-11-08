// Estados vigentes en accounts. Si agregan otro valor, se muestra tal cual (fallback).
export const STATUS_META = {
    activa: { label: 'Activa', tone: 'ok' },
    pendiente_verificacion: { label: 'Por verificar', tone: 'warn' },
    suspendida: { label: 'Suspendida', tone: 'danger' },
};

export const STATUS_OPTIONS = Object.entries(STATUS_META).map(([value, { label }]) => ({ value, label }));

export function getStatusMeta(status) {
    return STATUS_META[status] ?? { label: status ?? '—', tone: 'neutral' };
}

export const canSuspend = (status) => status !== 'suspendida';
export const canReactivate = (status) => status === 'suspendida';

/**
 * Convierte el error de apiRequest en un texto para la UI.
 * AJUSTAR a la forma real del error que lanza apiRequest ({code, detail, field_errors}).
 */
export function getErrorMessage(err, fallback = 'No se pudo completar la operación. Intenta de nuevo.') {
    const status = err?.status;
    if (status === 403) return 'No tienes permiso para realizar esta acción.';
    if (status === 404) return 'El cliente ya no existe o no está disponible.';
    return err?.data?.detail ?? err?.detail ?? fallback;
}

/** Mensaje de respuesta clara tras suspender/reactivar, según lo que devolvió el servidor. */
export function describeChange(action, { client, changed, sessions_invalidated: sessionsInvalidated }) {
    if (!changed) {
        return action === 'suspend'
            ? 'La cuenta ya estaba suspendida. No se hicieron cambios.'
            : 'La cuenta no estaba suspendida. No se hicieron cambios.';
    }
    if (action === 'suspend') {
        return `Cuenta suspendida.${sessionsInvalidated ? ' Se cerraron sus sesiones activas.' : ''} Sus archivos, plan, pagos e historial se conservan.`;
    }
    if (client.account_status === 'pendiente_verificacion') {
        return 'Cuenta reactivada. Sigue pendiente de verificar su correo, así que todavía no puede ingresar.';
    }
    return 'Cuenta reactivada. Las sesiones anteriores no se restauran: el cliente debe iniciar sesión de nuevo.';
}