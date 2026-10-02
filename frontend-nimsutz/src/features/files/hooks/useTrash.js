import { useState, useCallback, useEffect } from 'react';
import { transfersApi } from '@features/files/api/transfersApi';

// ─── helpers internos ──────────────────────────────────────────────────────────

/** Extrae mensaje de error legible desde cualquier valor capturado. */
function toErrorMessage(err, fallback = 'Ocurrió un error inesperado.') {
    const raw = err?.detail ?? err?.message ?? err;
    if (Array.isArray(raw)) return String(raw[0]);
    if (raw) return String(raw);
    return fallback;
}

// ─── hook ─────────────────────────────────────────────────────────────────────

/**
 * @typedef {Object} UseTrashResult
 * @property {Array}    trashedFiles
 * @property {boolean}  loading
 * @property {string|null} listError      - Error al cargar el listado
 * @property {string|null} busyId         - ID del archivo con operación en curso
 * @property {boolean}  emptying          - true mientras se vacía la papelera
 * @property {Function} loadTrash         - Recarga el listado manualmente
 * @property {Function} restoreFile       - (file) => Promise<{ ok, message }>
 * @property {Function} deleteFile        - (file) => Promise<{ ok, message }>
 * @property {Function} emptyTrash        - () => Promise<{ ok, message }>
 */

/**
 * @returns {UseTrashResult}
 */
export function useTrash() {
    const [trashedFiles, setTrashedFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [listError, setListError] = useState(null);
    const [busyId, setBusyId] = useState(null);
    const [emptying, setEmptying] = useState(false);

    const loadTrash = useCallback(async () => {
        setLoading(true);
        setListError(null);
        try {
            const files = await transfersApi.listarPapelera();
            setTrashedFiles(Array.isArray(files) ? files : []);
        } catch {
            setListError('No se pudo cargar la papelera. Inténtalo de nuevo.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadTrash(); }, [loadTrash]);

    /**
     * Restaura un archivo desde la papelera.
     * @param {{ id: number, original_name: string }} file
     * @returns {Promise<{ ok: boolean, message: string }>}
     */
    const restoreFile = async (file) => {
        setBusyId(file.id);
        try {
            await transfersApi.restaurar(file.id);
            await loadTrash();
            return { ok: true, message: `${file.original_name} restaurado correctamente.` };
        } catch (err) {
            return { ok: false, message: toErrorMessage(err, 'No se pudo restaurar el archivo.') };
        } finally {
            setBusyId(null);
        }
    };

    /**
     * Elimina un archivo definitivamente desde la papelera.
     * @param {{ id: number, original_name: string }} file
     * @returns {Promise<{ ok: boolean, message: string }>}
     */
    const deleteFile = async (file) => {
        setBusyId(file.id);
        try {
            await transfersApi.eliminarDefinitivamente(file.id);
            await loadTrash();
            return { ok: true, message: `${file.original_name} eliminado definitivamente.` };
        } catch (err) {
            return { ok: false, message: toErrorMessage(err, 'No se pudo eliminar el archivo.') };
        } finally {
            setBusyId(null);
        }
    };

    /**
     * Vacía toda la papelera eliminando todos los archivos definitivamente.
     * @returns {Promise<{ ok: boolean, message: string }>}
     */
    const emptyTrash = async () => {
        setEmptying(true);
        try {
            await Promise.all(
                trashedFiles.map((f) => transfersApi.eliminarDefinitivamente(f.id)),
            );
            await loadTrash();
            return { ok: true, message: 'Se vació la papelera correctamente.' };
        } catch (err) {
            return {
                ok: false,
                message: toErrorMessage(err, 'Error al vaciar la papelera.'),
            };
        } finally {
            setEmptying(false);
        }
    };

    return {
        trashedFiles,
        loading,
        listError,
        busyId,
        emptying,
        loadTrash,
        restoreFile,
        deleteFile,
        emptyTrash,
    };
}
