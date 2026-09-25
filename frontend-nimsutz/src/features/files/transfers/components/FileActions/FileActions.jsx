import { useState } from 'react';
import { Download, Trash2, Loader2, AlertTriangle } from 'lucide-react';
import { useTransfers } from '../../hooks/useTransfers';
import Modal from '@shared/components/Modal/Modal';
import Button from '@shared/components/Button/Button';
import styles from './FileActions.module.css';

/**
 * Acciones directas sobre un archivo en la fila del explorador.
 * Contrato A-B: recibe `file` y `onChanged`.
 */
export default function FileActions({ file, onChanged }) {
    const [busyAction, setBusyAction] = useState(null); // 'download' | 'trash' | null
    const [trashModalOpen, setTrashModalOpen] = useState(false);
    const { descargarArchivo, enviarAPapelera } = useTransfers();

    const handleDownload = async () => {
        setBusyAction('download');
        try {
            await descargarArchivo(file);
        } finally {
            setBusyAction(null);
        }
    };

    const handleConfirmTrash = async () => {
        setBusyAction('trash');
        try {
            await enviarAPapelera(file.id, onChanged);
            setTrashModalOpen(false);
        } finally {
            setBusyAction(null);
        }
    };

    return (
        <>
            <div className={styles.rowActions}>
                <button
                    type="button"
                    onClick={handleDownload}
                    className={styles.downloadBtn}
                    title={`Descargar ${file.original_name}`}
                    aria-label={`Descargar ${file.original_name}`}
                    disabled={Boolean(busyAction)}
                >
                    {busyAction === 'download' ? (
                        <Loader2 size={18} className={styles.spin} />
                    ) : (
                        <Download size={18} />
                    )}
                </button>

                <button
                    type="button"
                    onClick={() => setTrashModalOpen(true)}
                    className={styles.trashBtn}
                    title={`Mover "${file.original_name}" a papelera`}
                    aria-label={`Mover "${file.original_name}" a papelera`}
                    disabled={Boolean(busyAction)}
                >
                    {busyAction === 'trash' ? (
                        <Loader2 size={18} className={styles.spin} />
                    ) : (
                        <Trash2 size={18} />
                    )}
                </button>
            </div>

            {trashModalOpen && (
                <Modal
                    open={trashModalOpen}
                    onClose={() => !busyAction && setTrashModalOpen(false)}
                    title="Mover a papelera"
                    icon={<AlertTriangle size={20} />}
                >
                    <div className={styles.modalBody}>
                        <p className={styles.modalText}>
                            ¿Estás seguro de que deseas enviar el archivo{' '}
                            <strong className={styles.fileNameHighlight}>"{file.original_name}"</strong> a la papelera?
                        </p>
                        <p className={styles.modalSubtext}>
                            El archivo dejará de estar disponible en esta carpeta, pero podrás restaurarlo en cualquier momento desde la sección de papelera.
                        </p>
                        <div className={styles.modalActions}>
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={() => setTrashModalOpen(false)}
                                disabled={busyAction === 'trash'}
                            >
                                Cancelar
                            </Button>
                            <Button
                                type="button"
                                variant="danger"
                                onClick={handleConfirmTrash}
                                loading={busyAction === 'trash'}
                                loadingLabel="Moviendo..."
                            >
                                Mover a papelera
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}
        </>
    );
}