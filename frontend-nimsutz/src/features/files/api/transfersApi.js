/* Capa de peticiones HTTP para el módulo de transferencias (B - Rodrigo).
   Usa apiRequest del cliente compartido para reutilizar cookies de sesión
   y el token CSRF que maneja AuthProvider, tal como pide el contrato A-B. */

import { apiRequest } from '@shared/api/httpClient';

function json(body) {
    return {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    };
}

export const transfersApi = {
    /**
     * Obtiene las reglas de carga vigentes del servidor (tamaño máximo y
     * tipos permitidos). El front las usa solo para validar antes de subir;
     * la validación que protege es la del backend.
     * @returns {{ max_file_size_bytes: number, allowed_content_types: string[] }}
     */
    obtenerReglas: async () => {
        const data = await apiRequest('/api/files/upload-rules/');
        if (
            !Number.isFinite(data?.max_file_size_bytes) ||
            data.max_file_size_bytes <= 0 ||
            !Array.isArray(data?.allowed_content_types)
        ) {
            throw new Error('No se pudieron obtener las reglas de carga.');
        }
        return data;
    },

    /**
     * Paso 1: Solicita una reserva de cuota y la URL firmada para subir.
     * @param {{ folder: number, original_name: string, content_type: string, size_bytes: number }} data
     * @returns {{ file: object, upload_url: string }}
     */
    solicitarCarga: (data) =>
        apiRequest('/api/files/request-upload/', { method: 'POST', ...json(data) }),

    /**
     * Paso 3: Confirma que el PUT a MinIO se completó.
     * @param {number} fileId
     */
    confirmarCarga: (fileId) =>
        apiRequest(`/api/files/${fileId}/confirm-upload/`, { method: 'POST' }),

    /**
     * Genera URL firmada de descarga.
     * @param {number} fileId
     * @returns {{ download_url: string }}
     */
    solicitarDescarga: (fileId) =>
        apiRequest(`/api/files/${fileId}/request-download/`),

    /**
     * Envía el archivo a la papelera (eliminación lógica).
     * @param {number} fileId
     */
    moverAPapelera: (fileId) =>
        apiRequest(`/api/files/${fileId}/trash/`, { method: 'POST' }),

    /**
     * Lista archivos en papelera del usuario.
     * @returns {Array<object>}
     */
    listarPapelera: () =>
        apiRequest('/api/files/?status=trashed'),

    /**
     * Restaura un archivo desde la papelera.
     * @param {number} fileId
     * @param {string|null} newName  — nombre alternativo si hay conflicto
     */
    restaurar: (fileId, newName = null) =>
        apiRequest(`/api/files/${fileId}/restore/`, {
            method: 'POST',
            ...json(newName ? { new_name: newName } : {}),
        }),

    /**
     * Elimina el archivo físicamente de MinIO y su registro en BD.
     * @param {number} fileId
     */
    eliminarDefinitivamente: (fileId) =>
        apiRequest(`/api/files/${fileId}/permanent/`, { method: 'DELETE' }),
};
