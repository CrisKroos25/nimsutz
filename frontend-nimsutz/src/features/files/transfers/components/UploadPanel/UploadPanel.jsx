import { useState } from 'react';
import { UploadCloud, AlertTriangle, X } from 'lucide-react';
import { useTransfers } from '../../hooks/useTransfers';
import styles from './UploadPanel.module.css';

export default function UploadPanel({ folderId, onCompleted, onClose }) {
    const { subirArchivo, loading: isUploading, error, setError } = useTransfers();

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            subirArchivo(file, folderId, () => {
                if (onCompleted) onCompleted();
                if (onClose) onClose();
            });
        }
    };

    return (
        <div className={styles.overlay}>
            <div className={styles.modal}>
                <header className={styles.header}>
                    <div>
                        <h2 className={styles.title}>Subir archivo</h2>
                        <p className={styles.subtitle}>Máximo 25 MB - PDF, DOCX, TXT, PNG, JPG</p>
                    </div>
                    {onClose && (
                        <button onClick={onClose} className={styles.closeBtn}>
                            <X size={20} />
                        </button>
                    )}
                </header>

                {error ? (
                    <div className={styles.errorBox}>
                        <AlertTriangle className={styles.errorIcon} size={24} />
                        <div className={styles.errorText}>
                            <h4>Error al subir archivo</h4>
                            <p>
                                {error === 'size' && 'El archivo supera el límite permitido de 25 MB.'}
                                {error === 'type' && 'Formato no permitido. Solo PDF, DOCX, TXT, PNG y JPG.'}
                                {error !== 'size' && error !== 'type' && 'Error de red o almacenamiento insuficiente.'}
                            </p>
                        </div>
                        <button className={styles.retryBtn} onClick={() => setError(null)}>
                            Reintentar
                        </button>
                    </div>
                ) : (
                    <label className={styles.dropZone}>
                        <input type="file" onChange={handleFileSelect} className={styles.hiddenInput} disabled={isUploading} />
                        <div className={styles.iconWrapper}>
                            <UploadCloud size={32} color="white" />
                        </div>
                        <h3 className={styles.dropTitle}>
                            {isUploading ? 'Subiendo y procesando...' : 'Arrastra tu archivo aquí'}
                        </h3>
                        <p className={styles.dropSubtitle}>o haz clic para seleccionarlo</p>
                    </label>
                )}

                {/* SIMULADOR PARA PRUEBAS LOCALES */}
                <div className={styles.simulator}>
                    <span className={styles.simTitle}>SIMULAR ESTADO DE ERROR (PRUEBAS)</span>
                    <div className={styles.simButtons}>
                        <button onClick={() => setError('type')} className={styles.simBtn}>type</button>
                        <button onClick={() => setError('size')} className={styles.simBtn}>size</button>
                        <button onClick={() => setError('quota')} className={styles.simBtn}>quota</button>
                    </div>
                </div>
            </div>
        </div>
    );
}