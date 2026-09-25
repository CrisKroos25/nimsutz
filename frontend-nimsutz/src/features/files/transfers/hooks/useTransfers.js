/* Hook del módulo de transferencias (B - Rodrigo).
   Centraliza el estado de carga/error y las tres operaciones de B:
   subirArchivo, descargarArchivo y enviarAPapelera.
   El resto de operaciones de papelera (listar, restaurar, eliminar
   definitivamente) viven directamente en Trash.jsx porque ese componente
   maneja su propio ciclo de vida de listado. */

import { useState } from 'react';
import { transfersApi } from '../api/TransfersApi';

export function useTransfers() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /**
     * Sube un archivo al servidor en tres pasos:
     * 1. Solicita reserva y URL firmada a Django.
     * 2. Hace el PUT físico contra MinIO con la URL firmada.
     * 3. Confirma la carga al servidor.
     *
     * @param {File}        file       - Objeto File del input/drop
     * @param {number}      folderId   - ID de la carpeta destino (requerido)
     * @param {function}    onCompleted - Callback que recarga el listado de A
     */
    const subirArchivo = async (file, folderId, onCompleted) => {
        setLoading(true);
        setError(null);
        try {
            // Validación de tamaño (RN-E3-17: máximo 25 MB)
            if (file.size > 25 * 1024 * 1024) {
                throw new Error('El archivo supera el límite de 25 MB.');
            }

            // Detección y normalización de tipo MIME (RN-E3-18)
            let contentType = file.type;
            const ext = file.name.split('.').pop()?.toLowerCase();
            if (!contentType || contentType === 'application/octet-stream') {
                if (ext === 'pdf') contentType = 'application/pdf';
                else if (ext === 'png') contentType = 'image/png';
                else if (ext === 'jpg' || ext === 'jpeg') contentType = 'image/jpeg';
                else if (ext === 'txt') contentType = 'text/plain';
                else if (ext === 'docx') contentType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
            }

            const validTypes = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain',
                'image/png',
                'image/jpeg',
            ];
            if (!validTypes.includes(contentType)) {
                throw new Error('Tipo de archivo no permitido. Solo se permiten PDF, DOCX, TXT, PNG y JPG.');
            }

            // Paso 1: solicitar reserva de cuota y URL firmada
            const { file: reserva, upload_url } = await transfersApi.solicitarCarga({
                folder: folderId,
                original_name: file.name,
                content_type: contentType,
                size_bytes: file.size,
            });

            // Paso 2: PUT físico contra MinIO (no pasa por Django)
            const uploadResponse = await fetch(upload_url, {
                method: 'PUT',
                body: file,
                headers: { 'Content-Type': contentType },
            });
            if (!uploadResponse.ok) {
                throw new Error('Error al transferir el archivo al servidor.');
            }

            // Paso 3: confirmar al servidor que el PUT se completó
            await transfersApi.confirmarCarga(reserva.id);

            if (onCompleted) onCompleted();
        } catch (err) {
            const rawMsg = err?.detail || err?.message || 'Error al procesar el archivo.';
            const msg = Array.isArray(rawMsg) ? rawMsg[0] : String(rawMsg);
            setError(msg);
            if (onCompleted) onCompleted(new Error(msg));
        } finally {
            setLoading(false);
        }
    };

    /**
     * Solicita una URL firmada de descarga y la abre en el navegador.
     * @param {{ id: number, original_name: string }} file - Objeto de archivo
     */
    const descargarArchivo = async (file) => {
        try {
            const { download_url } = await transfersApi.solicitarDescarga(file.id);
            const link = document.createElement('a');
            link.href = download_url;
            link.setAttribute('download', file.original_name);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error('Error al descargar el archivo:', err);
            alert('No se pudo completar la descarga. Inténtalo de nuevo.');
        }
    };

    /**
     * Envía el archivo a la papelera (eliminación lógica).
     * @param {number}   fileId    - ID del archivo
     * @param {function} onChanged - Callback que recarga el listado de A
     */
    const enviarAPapelera = async (fileId, onChanged) => {
        try {
            await transfersApi.moverAPapelera(fileId);
            if (onChanged) onChanged();
        } catch (err) {
            console.error('Error al mover a papelera:', err);
            alert(err.message || 'Error al enviar el archivo a la papelera.');
        }
    };

    return { subirArchivo, descargarArchivo, enviarAPapelera, loading, error, setError };
}