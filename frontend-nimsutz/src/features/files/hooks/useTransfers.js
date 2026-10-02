import { useState } from 'react';
import { transfersApi } from '@features/files/api/transfersApi';
import { resolveMimeType, assertFileAllowed } from '@features/files/utils/mimeValidator';

// ─── helpers internos ──────────────────────────────────────────────────────────

/**
 * Extrae un mensaje de error legible desde cualquier valor capturado.
 * Normaliza arrays de DRF, objetos Error y strings.
 *
 * @param {unknown} err
 * @param {string}  fallback
 * @returns {string}
 */
function toErrorMessage(err, fallback = 'Ocurrió un error inesperado.') {
    const raw = err?.detail ?? err?.message ?? err;
    if (Array.isArray(raw)) return String(raw[0]);
    if (raw) return String(raw);
    return fallback;
}

/**
 * Crea y hace clic en un <a> temporal para desencadenar la descarga de una URL.
 *
 * @param {string} url
 * @param {string} filename
 */
function triggerDownload(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
}

// ─── hook ─────────────────────────────────────────────────────────────────────

export function useTransfers() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /**
     * Sube un archivo al servidor en tres pasos:
     * 1. Solicita reserva de cuota y URL firmada a Django.
     * 2. Hace el PUT físico a MinIO con la URL firmada.
     * 3. Confirma la carga al servidor.
     *
     * @param {File}                file
     * @param {number}              folderId   - ID de la carpeta destino
     * @param {(err?: Error)=>void} onCompleted - Callback de A; recibe Error si falla
     */
    const subirArchivo = async (file, folderId, onCompleted) => {
        setLoading(true);
        setError(null);
        try {
            const contentType = resolveMimeType(file);
            assertFileAllowed(file, contentType); // lanza si no cumple

            // Paso 1: reserva de cuota y URL firmada
            const { file: reserva, upload_url } = await transfersApi.solicitarCarga({
                folder: folderId,
                original_name: file.name,
                content_type: contentType,
                size_bytes: file.size,
            });

            // Paso 2: PUT directo a MinIO (no pasa por Django)
            const uploadResponse = await fetch(upload_url, {
                method: 'PUT',
                body: file,
                headers: { 'Content-Type': contentType },
            });
            if (!uploadResponse.ok) {
                throw new Error('Error al transferir el archivo al servidor.');
            }

            // Paso 3: confirmar al servidor
            await transfersApi.confirmarCarga(reserva.id);

            onCompleted?.();
        } catch (err) {
            const msg = toErrorMessage(err, 'Error al procesar el archivo.');
            setError(msg);
            onCompleted?.(new Error(msg));
        } finally {
            setLoading(false);
        }
    };

    /**
     * Solicita una URL firmada de descarga y la abre en el navegador.
     *
     * @param {{ id: number, original_name: string }} file
     */
    const descargarArchivo = async (file) => {
        try {
            const { download_url } = await transfersApi.solicitarDescarga(file.id);
            triggerDownload(download_url, file.original_name);
        } catch (err) {
            const msg = toErrorMessage(err, 'No se pudo completar la descarga.');
            // La descarga no tiene estado global de error; el componente debe manejarlo
            throw new Error(msg);
        }
    };

    /**
     * Envía el archivo a la papelera (eliminación lógica).
     * Lanza si la petición falla, para que FileActions gestione el error.
     *
     * @param {number} fileId
     */
    const enviarAPapelera = async (fileId) => {
        await transfersApi.moverAPapelera(fileId);
    };

    return {
        subirArchivo,
        descargarArchivo,
        enviarAPapelera,
        loading,
        error,
        setError,
    };
}
