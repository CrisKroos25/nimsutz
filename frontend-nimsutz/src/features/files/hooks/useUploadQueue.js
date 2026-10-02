/**
 * useUploadQueue.js  —  Módulo B (Rodrigo)
 *
 * SRP: Única responsabilidad → administrar la cola visual de subidas
 *      (estados Pendiente → Procesando → Subiendo → Disponible / Error,
 *      barra de progreso, animación de cancelación).
 *
 * OCP: La estrategia de animación para archivos pequeños vs. grandes está
 *      separada en funciones privadas; agregar una nueva estrategia no
 *      requiere modificar UploadPanel.jsx.
 *
 * ISP: Solo UploadPanel importa este hook; no expone nada que otros módulos usen.
 */

import { useState, useCallback } from 'react';
import { useTransfers } from './useTransfers';

// ─── constantes ───────────────────────────────────────────────────────────────

const SMALL_FILE_THRESHOLD = 500 * 1024; // 500 KB
const CANCEL_ANIMATION_MS  = 350;
const COMPLETE_HOLD_MS     = 1500;
const PROGRESS_INTERVAL_MS = 200;
const STEP_MIN = 6;
const STEP_MAX = 10;
const PROGRESS_CAP = 90;

// ─── helpers internos ─────────────────────────────────────────────────────────

/** Extrae mensaje de error legible desde cualquier valor capturado. */
function toErrorText(err) {
    if (typeof err === 'string') return err;
    return err?.message ? String(err.message) : 'Error al subir el archivo.';
}

/** Genera un ID de subida único. */
function newUploadId() {
    return Math.random().toString(36).slice(2, 11);
}

// ─── hook ─────────────────────────────────────────────────────────────────────

/**
 * @typedef {Object} UploadEntry
 * @property {string}  id
 * @property {string}  name
 * @property {number}  size
 * @property {'Pendiente'|'Procesando'|'Subiendo'|'Disponible'|'Error'} status
 * @property {number}  progress  (0-100, relevante solo en estado Subiendo)
 * @property {string|undefined} error
 * @property {boolean} isPopping (animación de salida)
 */

/**
 * @returns {{
 *   activeUploads: UploadEntry[],
 *   enqueue: (file: File) => void,
 *   cancel:  (uploadId: string) => void,
 * }}
 */
export function useUploadQueue(folderId, onCompleted) {
    const [activeUploads, setActiveUploads] = useState([]);
    const { subirArchivo } = useTransfers();

    // Actualiza un campo de un item concreto por ID
    const updateUpload = useCallback((id, patch) => {
        setActiveUploads((prev) =>
            prev.map((u) => (u.id === id ? { ...u, ...patch } : u)),
        );
    }, []);

    // Elimina el item de la lista (tras animación de pop)
    const removeUpload = useCallback((id) => {
        setActiveUploads((prev) => prev.filter((u) => u.id !== id));
    }, []);

    /**
     * Flujo para archivos pequeños (<500 KB):
     * Pendiente → Procesando → [subida real] → Disponible (o Error)
     */
    const runSmallUpload = useCallback((file, uploadId) => {
        setTimeout(() => {
            updateUpload(uploadId, { status: 'Procesando' });
            setTimeout(() => {
                subirArchivo(file, folderId, (err) => {
                    if (err) {
                        updateUpload(uploadId, { status: 'Error', error: toErrorText(err) });
                    } else {
                        updateUpload(uploadId, { status: 'Disponible' });
                        setTimeout(() => {
                            onCompleted?.();
                            removeUpload(uploadId);
                        }, COMPLETE_HOLD_MS);
                    }
                });
            }, 1000);
        }, 900);
    }, [folderId, subirArchivo, onCompleted, updateUpload, removeUpload]);

    /**
     * Flujo para archivos grandes (≥500 KB):
     * Pendiente → Procesando → Subiendo (con barra) → Disponible (o Error)
     */
    const runLargeUpload = useCallback((file, uploadId) => {
        setTimeout(() => {
            updateUpload(uploadId, { status: 'Procesando' });
            setTimeout(() => {
                updateUpload(uploadId, { status: 'Subiendo', progress: 10 });

                let current = 10;
                const interval = setInterval(() => {
                    if (current < PROGRESS_CAP) {
                        current = Math.min(
                            current + Math.floor(Math.random() * STEP_MAX) + STEP_MIN,
                            PROGRESS_CAP,
                        );
                        updateUpload(uploadId, { progress: current });
                    }
                }, PROGRESS_INTERVAL_MS);

                subirArchivo(file, folderId, (err) => {
                    clearInterval(interval);
                    if (err) {
                        updateUpload(uploadId, { status: 'Error', error: toErrorText(err) });
                    } else {
                        updateUpload(uploadId, { progress: 100 });
                        setTimeout(() => {
                            updateUpload(uploadId, { status: 'Disponible' });
                            setTimeout(() => {
                                onCompleted?.();
                                removeUpload(uploadId);
                            }, COMPLETE_HOLD_MS);
                        }, 650);
                    }
                });
            }, 1500);
        }, 900);
    }, [folderId, subirArchivo, onCompleted, updateUpload, removeUpload]);

    /**
     * Encola un archivo para subida y arranca su flujo visual.
     * @param {File} file
     */
    const enqueue = useCallback((file) => {
        const uploadId = newUploadId();
        const isSmall = file.size < SMALL_FILE_THRESHOLD;

        setActiveUploads((prev) => [
            { id: uploadId, name: file.name || 'Archivo', size: file.size || 0,
              status: 'Pendiente', progress: 0, isPopping: false },
            ...prev,
        ]);

        if (isSmall) {
            runSmallUpload(file, uploadId);
        } else {
            runLargeUpload(file, uploadId);
        }
    }, [runSmallUpload, runLargeUpload]);

    /**
     * Cancela una subida con animación de "pop de burbuja".
     * @param {string} uploadId
     */
    const cancel = useCallback((uploadId) => {
        updateUpload(uploadId, { isPopping: true });
        setTimeout(() => removeUpload(uploadId), CANCEL_ANIMATION_MS);
    }, [updateUpload, removeUpload]);

    return { activeUploads, enqueue, cancel };
}
