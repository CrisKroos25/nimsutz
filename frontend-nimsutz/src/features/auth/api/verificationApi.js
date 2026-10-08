import { apiRequest } from '@shared/api/httpClient';

function json(body) {
    return {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    };
}

export const verificationApi = {
    /**
     * Valida el token de verificación y activa la cuenta.
     * @param {string} token
     * @returns {Promise<{detail: string}>}
     */
    verifyEmail: (token) =>
        apiRequest('/api/auth/verify-email/', { 
            method: 'POST', 
            ...json({ token }) 
        }),

    /**
     * Reenvía el correo de verificación.
     * @param {string} email
     * @returns {Promise<{detail: string}>}
     */
    resendVerification: (email) =>
        apiRequest('/api/auth/resend-verification/', { 
            method: 'POST', 
            ...json({ email }) 
        }),
};

