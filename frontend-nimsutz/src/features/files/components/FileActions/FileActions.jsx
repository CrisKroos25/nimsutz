import { useState } from 'react';
import { Download, Trash2, Loader2, AlertTriangle } from 'lucide-react';
import { useTransfers } from '@features/files/hooks/useTransfers';
import Modal from '@shared/components/Modal/Modal';
import Button from '@shared/components/Button/Button';
import styles from './FileActions.module.css';

// ─── constantes ───────────────────────────────────────────────────────────────

/** Identificadores de acción para el estado `busyAction`. */
const ACTION = Object.freeze({ DOWNLOAD: 'download', TRASH: 'trash' });

// ─── sub-componente: modal de confirmación de papelera ────────────────────────

/**
 * @param {{
 *   fileName: string,
 *   busy: boolean,
 *   onConfirm: () => void,
 *   onClose: () => void,
 * }} props
 */
function TrashConfirmModal({ fileName, busy, onConfirm, onClose }) {
    return (
        <Modal
            open
            onClose={() => !busy && onClose()}
            title="Mover a papelera"
            icon={<AlertTriangle size={20} />}
        >
            <div className={styles.modalBody}>
                <p className={styles.modalText}>
                    ¿Estás seguro de que deseas enviar el archivo{' '}
                    <strong className={styles.fileNameHighlight}>
                        &ldquo;{fileName}&rdquo;
                    </strong>{' '}
                    a la papelera?
                </p>
                <p className={styles.modalSubtext}>
                    El archivo dejará de estar disponible en esta carpeta,
                    pero podrás restaurarlo en cualquier momento desde la
                    sección de papelera.
                </p>
                <div className={styles.modalActions}>
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={onClose}
                        disabled={busy}
                    >
                        Cancelar
                    </Button>
                    <Button
                        type="button"
                        variant="danger"
                        onClick={onConfirm}
                        loading={busy}
                        loadingLabel="Moviendo..."
                    >
                        Mover a papelera
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

// ─── componente principal ─────────────────────────────────────────────────────

/**
 * Botones de acción para un archivo en la fila del explorador.
 *
 * @param {{ file: object, onChanged: () => void }} props
 */
export default function FileActions({ file, onChanged }) {
    const [busyAction, setBusyAction] = useState(null);
    const [trashModalOpen, setTrashModalOpen] = useState(false);
    const { descargarArchivo, enviarAPapelera } = useTransfers();

    const isDownloading = busyAction === ACTION.DOWNLOAD;
    const isTrashing    = busyAction === ACTION.TRASH;

    const handleDownload = async () => {
        setBusyAction(ACTION.DOWNLOAD);
        try {
            await descargarArchivo(file);
        } catch (err) {
            // La descarga falló; mostramos alerta mínima ya que no hay estado
            // de error global en FileActions (ISP: onChanged no es para errores).
            window.alert(err.message ?? 'No se pudo completar la descarga.');
        } finally {
            setBusyAction(null);
        }
    };

    const handleConfirmTrash = async () => {
        setBusyAction(ACTION.TRASH);
        try {
            await enviarAPapelera(file.id);
            setTrashModalOpen(false);
            onChanged?.();
        } catch (err) {
            window.alert(err.message ?? 'Error al enviar el archivo a la papelera.');
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
                    {isDownloading ? <Loader2 size={18} className={styles.spin} /> : <Download size={18} />}
                </button>

                <button
                    type="button"
                    onClick={() => setTrashModalOpen(true)}
                    className={styles.trashBtn}
                    title={`Mover "${file.original_name}" a papelera`}
                    aria-label={`Mover "${file.original_name}" a papelera`}
                    disabled={Boolean(busyAction)}
                >
                    {isTrashing ? <Loader2 size={18} className={styles.spin} /> : <Trash2 size={18} />}
                </button>
            </div>

            {trashModalOpen && (
                <TrashConfirmModal
                    fileName={file.original_name}
                    busy={isTrashing}
                    onConfirm={handleConfirmTrash}
                    onClose={() => setTrashModalOpen(false)}
                />
            )}
        </>
    );
}
