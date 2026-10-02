import { useState } from 'react';
import {
    RotateCcw, Trash2, X, Loader2, AlertTriangle,
} from 'lucide-react';

import { useTrash } from '@features/files/hooks/useTrash';
import { getFileTypeInfo } from '@features/files/utils/fileTypeInfo';
import { formatBytes, formatDate } from '@features/files/utils/formatters';
import '@features/files/styles/responsive.css';

import Modal from '@shared/components/Modal/Modal';
import Button from '@shared/components/Button/Button';
import styles from './Trash.module.css';

// ─── sub-componente: fila de archivo en la tabla ──────────────────────────────

/**
 * @param {{
 *   file:      object,
 *   isBusy:    boolean,
 *   emptying:  boolean,
 *   onRestore: (file: object) => void,
 *   onDelete:  (file: object) => void,
 * }} props
 */
function TrashRow({ file, isBusy, emptying, onRestore, onDelete }) {
    const typeInfo = getFileTypeInfo(file.content_type, file.original_name, styles);
    const IconComponent = typeInfo.icon;

    return (
        <div className={styles.tableRow} data-table="row">
            <div className={styles.cellName} data-cell="name">
                <div className={`${styles.iconBadge} ${typeInfo.className}`}>
                    <IconComponent size={18} />
                </div>
                <div className={styles.nameMeta}>
                    <span className={styles.fileName} title={file.original_name}>
                        {file.original_name}
                    </span>
                </div>
            </div>

            <div className={styles.cellType} data-cell="type">
                <span className={`${styles.typeBadge} ${typeInfo.className}`}>
                    {typeInfo.label}
                </span>
            </div>

            <div className={styles.cellDate} data-cell="date">
                {formatDate(file.trashed_at ?? file.updated_at)}
            </div>

            <div className={styles.cellSize} data-cell="size">
                {formatBytes(file.size_bytes)}
            </div>

            <div className={styles.cellActions} data-cell="actions">
                <button
                    type="button"
                    onClick={() => onRestore(file)}
                    className={styles.restoreBtn}
                    title="Restaurar archivo"
                    disabled={isBusy || emptying}
                >
                    {isBusy
                        ? <Loader2 size={15} className={styles.spin} />
                        : <RotateCcw size={15} />}
                    <span>Restaurar</span>
                </button>

                <button
                    type="button"
                    onClick={() => onDelete(file)}
                    className={styles.deleteBtn}
                    title="Eliminar definitivamente"
                    disabled={isBusy || emptying}
                >
                    {isBusy
                        ? <Loader2 size={15} className={styles.spin} />
                        : <Trash2 size={15} />}
                    <span>Eliminar</span>
                </button>
            </div>
        </div>
    );
}

// ─── sub-componente: modal de confirmación de eliminación individual ──────────

function DeleteConfirmModal({ file, busy, onConfirm, onClose }) {
    return (
        <Modal
            open
            onClose={() => !busy && onClose()}
            title="Eliminar definitivamente"
            icon={<AlertTriangle size={20} />}
        >
            <div className={styles.modalBody}>
                <p className={styles.modalText}>
                    ¿Estás seguro de que deseas eliminar permanentemente el archivo{' '}
                    <strong className={styles.fileNameHighlight}>
                        &ldquo;{file.original_name}&rdquo;
                    </strong>
                    ?
                </p>
                <p className={styles.modalSubtext}>
                    Esta acción borrará el archivo físicamente del almacenamiento
                    y liberará cuota. No se puede deshacer.
                </p>
                <div className={styles.modalActions}>
                    <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
                        Cancelar
                    </Button>
                    <Button
                        type="button" variant="danger"
                        onClick={onConfirm} loading={busy} loadingLabel="Eliminando..."
                    >
                        Eliminar definitivamente
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

// ─── sub-componente: modal de vaciado de papelera ────────────────────────────

function EmptyTrashModal({ count, busy, onConfirm, onClose }) {
    return (
        <Modal
            open
            onClose={() => !busy && onClose()}
            title="Vaciar papelera"
            icon={<AlertTriangle size={20} />}
        >
            <div className={styles.modalBody}>
                <p className={styles.modalText}>
                    ¿Estás seguro de que deseas eliminar definitivamente{' '}
                    <strong>{count} {count === 1 ? 'archivo' : 'archivos'}</strong>{' '}
                    que se encuentran en la papelera?
                </p>
                <p className={styles.modalSubtext}>
                    Todos los archivos se borrarán físicamente de manera permanente
                    y se liberará su cuota de almacenamiento. Esta acción no se puede deshacer.
                </p>
                <div className={styles.modalActions}>
                    <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
                        Cancelar
                    </Button>
                    <Button
                        type="button" variant="danger"
                        onClick={onConfirm} loading={busy} loadingLabel="Vaciando papelera..."
                    >
                        Vaciar toda la papelera
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

// ─── sub-componente: toast de notificación ────────────────────────────────────

function Toast({ message, type, onClose }) {
    return (
        <div
            className={`${styles.toast} ${type === 'error' ? styles.toastError : styles.toastSuccess}`}
            role="status"
        >
            <span className={styles.toastMessage}>{message}</span>
            <button
                type="button"
                onClick={onClose}
                className={styles.toastCloseBtn}
                aria-label="Cerrar notificación"
            >
                <X size={16} />
            </button>
        </div>
    );
}

// ─── página principal ─────────────────────────────────────────────────────────

/**
 * Página autónoma de Papelera.
 * A la monta en /trash; B gestiona su contenido y sus peticiones.
 */
export default function Trash() {
    const {
        trashedFiles, loading, listError, busyId, emptying,
        loadTrash, restoreFile, deleteFile, emptyTrash,
    } = useTrash();

    const [toast, setToast]                   = useState(null);
    const [deleteTarget, setDeleteTarget]     = useState(null);
    const [emptyModalOpen, setEmptyModalOpen] = useState(false);

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 4000);
    };

    const handleRestore = async (file) => {
        const result = await restoreFile(file);
        showToast(result.message, result.ok ? 'success' : 'error');
    };

    const handleDeleteRequest = (file) => setDeleteTarget(file);

    const handleConfirmDelete = async () => {
        const result = await deleteFile(deleteTarget);
        setDeleteTarget(null);
        showToast(result.message, result.ok ? 'success' : 'error');
    };

    const handleConfirmEmpty = async () => {
        const result = await emptyTrash();
        setEmptyModalOpen(false);
        showToast(result.message, result.ok ? 'success' : 'error');
    };

    return (
        <div className={styles.container}>
            <header className={styles.headerArea}>
                <div className={styles.headerText}>
                    <h1 className={styles.title}>Papelera</h1>
                    <p className={styles.subtitle}>
                        Los archivos eliminados se conservan aquí. Restáuralos o
                        elimínalos definitivamente cuando ya no los necesites.
                    </p>
                </div>

                <div className={styles.headerActions} data-element="toolbar">
                    <Button
                        type="button"
                        variant="danger"
                        onClick={() => setEmptyModalOpen(true)}
                        disabled={trashedFiles.length === 0 || loading || emptying}
                    >
                        <Trash2 size={16} /> Vaciar papelera
                    </Button>
                </div>
            </header>

            {listError && (
                <div className={styles.errorBanner} role="alert">
                    <span>{listError}</span>
                    <button onClick={loadTrash} className={styles.retryBtn}>
                        Reintentar
                    </button>
                </div>
            )}

            <div className={styles.tableCard}>
                <div className={styles.tableHeader} data-table="header">
                    <div className={styles.thName}>NOMBRE</div>
                    <div className={styles.thType}>TIPO</div>
                    <div className={styles.thDate}>ELIMINADO</div>
                    <div className={styles.thSize}>TAMAÑO</div>
                    <div className={styles.thActions}>ACCIONES</div>
                </div>

                {loading ? (
                    <div className={styles.loadingState}>
                        <Loader2 size={36} className={styles.spin} />
                        <p>Cargando papelera…</p>
                    </div>
                ) : trashedFiles.length === 0 ? (
                    <div className={styles.emptyState}>
                        <Trash2 size={44} className={styles.emptyIcon} />
                        <h3>La papelera está vacía</h3>
                        <p>Los archivos que envíes a la papelera aparecerán en este apartado.</p>
                    </div>
                ) : (
                    <div className={styles.tableBody}>
                        {trashedFiles.map((file) => (
                            <TrashRow
                                key={file.id}
                                file={file}
                                isBusy={busyId === file.id}
                                emptying={emptying}
                                onRestore={handleRestore}
                                onDelete={handleDeleteRequest}
                            />
                        ))}
                    </div>
                )}
            </div>

            {deleteTarget && (
                <DeleteConfirmModal
                    file={deleteTarget}
                    busy={Boolean(busyId)}
                    onConfirm={handleConfirmDelete}
                    onClose={() => setDeleteTarget(null)}
                />
            )}

            {emptyModalOpen && (
                <EmptyTrashModal
                    count={trashedFiles.length}
                    busy={emptying}
                    onConfirm={handleConfirmEmpty}
                    onClose={() => setEmptyModalOpen(false)}
                />
            )}

            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}
        </div>
    );
}
