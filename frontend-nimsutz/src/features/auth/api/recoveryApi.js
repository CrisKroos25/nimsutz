import { apiRequest } from '@shared/api/httpClient';

function json(body) {
    return {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    };
}

export const recoveryApi = {
    /**
     * Pide el enlace de recuperación. La respuesta es la misma exista o no la
     * cuenta, así que nunca confirma si un correo está registrado.
     * @param {string} email
     * @returns {Promise<{detail: string}>}
     */
    requestReset: (email) =>
        apiRequest('/api/auth/password-reset/', { method: 'POST', ...json({ email }) }),

    /**
     * Cambia la contraseña con el token del enlace (un solo uso, con vencimiento).
     * Errores: 401 si el token no sirve, 400 con `new_password` si la contraseña
     * no pasa los validadores del servidor.
     * @param {string} token
     * @param {string} newPassword
     * @returns {Promise<{detail: string}>}
     */
    confirmReset: (token, newPassword) =>
        apiRequest('/api/auth/password-reset/confirm/', {
            method: 'POST',
            ...json({ token, new_password: newPassword }),
        }),
};

// Un fallo de red no trae `status`; el mensaje del navegador viene en inglés.
export function recoveryMessage(failure) {
    return failure?.status
        ? failure.message
        : 'No se pudo conectar. Revisa tu conexión e inténtalo de nuevo.';
}
