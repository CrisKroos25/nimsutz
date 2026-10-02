/**
 * UploadPanel.jsx  —  Módulo B (Rodrigo)
 *
 * SRP: Este componente solo gestiona la UI del panel de subida:
 *      - Capturar el archivo (click o drag-and-drop)
 *      - Mostrar la lista de transferencias activas
 *      Toda la lógica de estado vive en useUploadQueue.js.
 *
 * Contrato A-B: recibe `folderId` y `onCompleted`.
 *              Al confirmar una carga exitosa, invoca `onCompleted` para
 *              que A recargue su listado. No modifica el explorador de A.
 */

import { useState } from 'react';
import { UploadCloud, X } from 'lucide-react';
import { useUploadQueue } from '@features/files/hooks/useUploadQueue';
import styles from './UploadPanel.module.css';

// ─── sub-componente: ítem de subida ───────────────────────────────────────────

const CANCELLABLE_STATUSES = new Set(['Subiendo', 'Procesando', 'Error']);

/**
 * Renderiza una fila de la lista de transferencias activas.
 *
 * @param {{ upload: import('../../../hooks/useUploadQueue').UploadEntry, onCancel: (id: string)=>void }} props
 */
function UploadItem({ upload, onCancel }) {
    const isCancellable = CANCELLABLE_STATUSES.has(upload.status);

    return (
        <div className={`${styles.uploadItem} ${upload.isPopping ? styles.popping : ''}`}>
            <div className={styles.uploadInfo}>
                <span className={styles.uploadName}>{upload.name}</span>

                {upload.status === 'Subiendo' ? (
                    <div className={styles.progressContainer}>
                        <div
                            className={styles.progressBar}
                            style={{ width: `${upload.progress}%` }}
                        />
                    </div>
                ) : (
                    <span className={`${styles.statusBadge} ${styles[upload.status.toLowerCase()] ?? ''}`}>
                        {upload.status}
                    </span>
                )}

                {upload.error && (
                    <span className={styles.uploadError}>{upload.error}</span>
                )}
            </div>

            {isCancellable && (
                <button
                    type="button"
                    className={styles.cancelBtn}
                    onClick={() => onCancel(upload.id)}
                    aria-label={`Cancelar subida de ${upload.name}`}
                >
                    <X size={16} />
                </button>
            )}
        </div>
    );
}

// ─── sub-componente: zona de drag-and-drop ────────────────────────────────────

/**
 * @param {{ onFile: (file: File) => void }} props
 */
function DropZone({ onFile }) {
    const [isDragging, setIsDragging] = useState(false);

    const handleSelect = (e) => {
        const file = e.target.files?.[0];
        if (file) onFile(file);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) onFile(file);
    };

    return (
        <label
            className={`${styles.dropZone} ${isDragging ? styles.dragging : ''}`}
            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
            onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
            onDrop={handleDrop}
        >
            <input type="file" onChange={handleSelect} className={styles.hiddenInput} />
            <div className={styles.iconWrapper}>
                <UploadCloud size={32} />
            </div>
            <h3 className={styles.dropTitle}>Arrastra tu archivo aquí</h3>
            <p className={styles.dropSubtitle}>o haz clic para seleccionarlo</p>
        </label>
    );
}

// ─── componente principal ─────────────────────────────────────────────────────

/**
 * Panel modal de subida de archivos.
 *
 * @param {{ folderId: number, onCompleted: ()=>void, onClose: ()=>void }} props
 */
export default function UploadPanel({ folderId, onCompleted, onClose }) {
    const { activeUploads, enqueue, cancel } = useUploadQueue(folderId, onCompleted);

    return (
        <div
            className={styles.overlay}
            onClick={onClose}
            data-component="upload-panel"
        >
            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
                <header className={styles.header}>
                    <div>
                        <h2 className={styles.title}>Gestor de Subidas</h2>
                        <p className={styles.subtitle}>Sube tus archivos a la carpeta actual</p>
                    </div>
                    {onClose && (
                        <button
                            type="button"
                            onClick={onClose}
                            className={styles.closeBtn}
                            aria-label="Cerrar gestor de subidas"
                        >
                            <X size={20} />
                        </button>
                    )}
                </header>

                <DropZone onFile={enqueue} />

                {activeUploads.length > 0 && (
                    <div className={styles.uploadsList}>
                        <h4 className={styles.listTitle}>Transferencias activas</h4>
                        {activeUploads.map((u) => (
                            <UploadItem key={u.id} upload={u} onCancel={cancel} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
