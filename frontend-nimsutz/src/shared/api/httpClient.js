let csrfToken;

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
        const error = new Error(data?.detail || 'No se pudo completar la solicitud. Inténtalo de nuevo.');
        error.status = response.status;
        throw error;
    }
    if (data?.csrfToken) csrfToken = data.csrfToken;
    return data;
}
