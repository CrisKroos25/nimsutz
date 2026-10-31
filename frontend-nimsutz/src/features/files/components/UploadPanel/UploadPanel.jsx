import { useState, useCallback } from 'react';
import { UploadCloud, X } from 'lucide-react';
import { useTransfers } from '@features/files/hooks/useTransfers';
import Modal from '@shared/components/Modal/Modal';
import styles from './UploadPanel.module.css';

export default function UploadPanel({ folderId, onCompleted, onClose }) {
    const [isDragging, setIsDragging] = useState(false);
    const [activeUploads, setActiveUploads] = useState([]);
    const { subirArchivo } = useTransfers();

    const processUpload = useCallback(
        (file) => {
            const uploadId = Math.random().toString(36).substr(2, 9);
            const isSmall = file.size < 500 * 1024;

            setActiveUploads((prev) => [
                {
                    id: uploadId,
                    file,
                    name: file.name || 'Archivo',
                    size: file.size || 0,
                    status: 'Pendiente',
                    progress: 0,
                    isSmall,
                },
                ...prev,
            ]);

            if (isSmall) {
                setTimeout(() => {
                    setActiveUploads((prev) =>
                        prev.map((u) =>
                            u.id === uploadId
                                ? { ...u, status: 'Procesando' }
                                : u,
                        ),
                    );
                    setTimeout(() => {
                        subirArchivo(file, folderId, (err) => {
                            if (err) {
                                const errorText =
                                    typeof err === 'string'
                                        ? err
                                        : err?.message
                                          ? String(err.message)
                                          : 'Error al subir';
                                setActiveUploads((prev) =>
                                    prev.map((u) =>
                                        u.id === uploadId
                                            ? {
                                                  ...u,
                                                  status: 'Error',
                                                  error: errorText,
                                              }
                                            : u,
                                    ),
                                );
                            } else {
                                setActiveUploads((prev) =>
                                    prev.map((u) =>
                                        u.id === uploadId
                                            ? { ...u, status: 'Disponible' }
                                            : u,
                                    ),
                                );
                                setTimeout(() => {
                                    if (onCompleted) onCompleted();
                                    setActiveUploads((prev) =>
                                        prev.filter((u) => u.id !== uploadId),
                                    );
                                }, 1500);
                            }
                        });
                    }, 1000);
                }, 900);
            } else {
                setTimeout(() => {
                    setActiveUploads((prev) =>
                        prev.map((u) =>
                            u.id === uploadId
                                ? { ...u, status: 'Procesando' }
                                : u,
                        ),
                    );
                    setTimeout(() => {
                        setActiveUploads((prev) =>
                            prev.map((u) =>
                                u.id === uploadId
                                    ? { ...u, status: 'Subiendo', progress: 10 }
                                    : u,
                            ),
                        );

                        let currentProgress = 10;
                        const progressInterval = setInterval(() => {
                            if (currentProgress < 90) {
                                currentProgress +=
                                    Math.floor(Math.random() * 10) + 6;
                                if (currentProgress > 90) currentProgress = 90;
                                setActiveUploads((prev) =>
                                    prev.map((u) =>
                                        u.id === uploadId
                                            ? {
                                                  ...u,
                                                  progress: currentProgress,
                                              }
                                            : u,
                                    ),
                                );
                            }
                        }, 200);

                        subirArchivo(file, folderId, (err) => {
                            clearInterval(progressInterval);
                            if (err) {
                                const errorText =
                                    typeof err === 'string'
                                        ? err
                                        : err?.message
                                          ? String(err.message)
                                          : 'Error al subir';
                                setActiveUploads((prev) =>
                                    prev.map((u) =>
                                        u.id === uploadId
                                            ? {
                                                  ...u,
                                                  status: 'Error',
                                                  error: errorText,
                                              }
                                            : u,
                                    ),
                                );
                            } else {
                                setActiveUploads((prev) =>
                                    prev.map((u) =>
                                        u.id === uploadId
                                            ? { ...u, progress: 100 }
                                            : u,
                                    ),
                                );
                                setTimeout(() => {
                                    setActiveUploads((prev) =>
                                        prev.map((u) =>
                                            u.id === uploadId
                                                ? { ...u, status: 'Disponible' }
                                                : u,
                                        ),
                                    );
                                    setTimeout(() => {
                                        if (onCompleted) onCompleted();
                                        setActiveUploads((prev) =>
                                            prev.filter(
                                                (u) => u.id !== uploadId,
                                            ),
                                        );
                                    }, 1500);
                                }, 650);
                            }
                        });
                    }, 1500);
                }, 900);
            }
        },
        [folderId, subirArchivo, onCompleted],
    );

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0];
        if (file) processUpload(file);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) processUpload(file);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    };

    const dismissUpload = (uploadId) => {
        setActiveUploads((prev) =>
            prev.map((u) =>
                u.id === uploadId ? { ...u, isPopping: true } : u,
            ),
        );
        setTimeout(() => {
            setActiveUploads((prev) => prev.filter((u) => u.id !== uploadId));
        }, 350);
    };

    return (
        <Modal open onClose={onClose} title="Gestor de subidas"
            description="Sube tus archivos a la carpeta actual"
            className={styles.modal}
            headerAction={<button type="button" onClick={onClose} className={styles.closeBtn} aria-label="Cerrar gestor de subidas"><X size={20} aria-hidden="true" /></button>}>
            <div data-component="upload-panel">
                <label
                    className={`${styles.dropZone} ${isDragging ? styles.dragging : ''}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        aria-label="Seleccionar archivo"
                        onChange={handleFileSelect}
                        className={styles.hiddenInput}
                    />
                    <div className={styles.iconWrapper}>
                        <UploadCloud size={32} />
                    </div>
                    <h3 className={styles.dropTitle}>
                        Arrastra tu archivo aquí
                    </h3>
                    <p className={styles.dropSubtitle}>
                        o haz clic para seleccionarlo
                    </p>
                </label>

                {activeUploads.length > 0 && (
                    <div className={styles.uploadsList}>
                        <h4 className={styles.listTitle}>
                            Transferencias activas
                        </h4>
                        {activeUploads.map((u) => (
                            <div
                                key={u.id}
                                className={`${styles.uploadItem} ${u.isPopping ? styles.popping : ''}`}
                            >
                                <div className={styles.uploadInfo}>
                                    <span className={styles.uploadName}>
                                        {u.name}
                                    </span>
                                    {u.status === 'Subiendo' ? (
                                        <div
                                            className={styles.progressContainer}
                                        >
                                            <div
                                                className={styles.progressBar}
                                                style={{
                                                    width: `${u.progress}%`,
                                                }}
                                            ></div>
                                        </div>
                                    ) : (
                                        <span
                                            className={`${styles.statusBadge} ${styles[u.status.toLowerCase()] || ''}`}
                                        >
                                            {u.status}
                                        </span>
                                    )}
                                    {u.error && (
                                        <span className={styles.uploadError}>
                                            {u.error}
                                        </span>
                                    )}
                                </div>
                                {['Subiendo', 'Procesando', 'Error'].includes(
                                    u.status,
                                ) && (
                                    <button
                                        type="button"
                                        className={styles.cancelBtn}
                                        aria-label={`Ocultar estado de ${u.name}`}
                                        onClick={() => dismissUpload(u.id)}
                                    >
                                        <X size={16} />
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </Modal>
    );
}
