let csrfToken;
let sessionCheck = null;

export const SESSION_EXPIRED_EVENT = 'auth:session-expired';

// Ante un 401/403 se pregunta al servidor si la sesión sigue viva. Las peticiones
// paralelas (useFiles lanza tres a la vez) comparten una sola comprobación.
function checkSessionStillAlive() {
    if (!sessionCheck) {
        sessionCheck = apiRequest('/api/auth/session/')
            .then((data) => {
                if (!data?.user) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
            })
            .catch(() => { /* Sin red o error del servidor: no se cierra la sesión por suposición. */ })
            .finally(() => { sessionCheck = null; });
    }
    return sessionCheck;
}

export async function apiRequest(path, options = {}) {
    if (!path.startsWith('/api/')) throw new Error('La ruta debe comenzar con /api/.');
    const method = (options.method || 'GET').toUpperCase();
    const mutates = !['GET', 'HEAD', 'OPTIONS'].includes(method);
    if (mutates && !csrfToken) await apiRequest('/api/auth/session/');
    const headers = new Headers(options.headers);
    if (mutates) headers.set('X-CSRFToken', csrfToken);
    const response = await fetch(path, { ...options, method, headers, credentials: 'same-origin' });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        // Login, logout y recuperación usan 401/403 por motivos propios (credenciales, CSRF).
        if ([401, 403].includes(response.status) && !path.startsWith('/api/auth/')) {
            void checkSessionStillAlive();
        }
        const detail = typeof data?.detail === 'string' ? data.detail : null;
        const error = new Error(detail || 'No se pudo completar la solicitud. Inténtalo de nuevo.');
        error.status = response.status;
        error.code = data?.code;
        // DRF devuelve campos en la raíz; el contrato nuevo también permite field_errors.
        error.fieldErrors = data?.field_errors || Object.fromEntries(
            Object.entries(data || {}).filter(([key]) => !['detail', 'code'].includes(key)),
        );
        throw error;
    }
    if (data?.csrfToken) csrfToken = data.csrfToken;
    return data;
}