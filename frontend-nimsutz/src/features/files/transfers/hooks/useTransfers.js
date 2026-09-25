import { useState } from 'react';
import { transfersApi } from '../api/TransfersApi';

export function useTransfers() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const subirArchivo = async (file, folderId, onCompleted) => {
        setLoading(true);
        setError(null);
        try {
            // 1. Validación de tamaño (Máximo 25 MB)[cite: 6]
            if (file.size > 25 * 1024 * 1024) {
                throw new Error('size');
            }

            // 2. Validación de formatos permitidos[cite: 6]
            const validTypes = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain',
                'image/png',
                'image/jpeg'
            ];
            if (!validTypes.includes(file.type)) {
                throw new Error('type');
            }

            // 3. Solicitar reserva y URL de carga a Django[cite: 6]
            const { data: reserva } = await transfersApi.solicitarCarga({
                nombre: file.name,
                tamano_bytes: file.size,
                tipo_mime: file.type,
                id_carpeta: folderId || null
            });

            // 4. Subida física (hacia MinIO o endpoint autorizado)[cite: 6]
            await fetch(reserva.upload_url, {
                method: 'PUT',
                body: file
            });

            // 5. Confirmar éxito[cite: 1, 6]
            await transfersApi.confirmarCarga(reserva.id);

            if (onCompleted) onCompleted();
        } catch (err) {
            setError(err.message || 'network');
        } finally {
            setLoading(false);
        }
    };

    const descargarArchivo = async (archivo) => {
        try {
            const data = await transfersApi.solicitarDescarga(archivo.id);
            const link = document.createElement('a');
            link.href = data.download_url;
            link.setAttribute('download', archivo.nombre);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Error al descargar el archivo:", err);
            alert("No se pudo completar la descarga.");
        }
    };

    const enviarAPapelera = async (archivoId, onChanged) => {
        try {
            await transfersApi.moverAPapelera(archivoId);
            if (onChanged) onChanged();
        } catch (err) {
            console.error("Error al mover a papelera:", err);
            alert("Error al enviar el archivo a la papelera.");
        }
    };

    return { subirArchivo, descargarArchivo, enviarAPapelera, loading, error, setError };
}