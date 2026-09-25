import { useCallback, useEffect, useState } from 'react';
import {
    RotateCcw,
    Trash2,
    X,
    Loader2,
    FileText,
    Image as ImageIcon,
    File as FileGenericIcon,
    AlertTriangle,
} from 'lucide-react';
import { transfersApi } from '../../api/TransfersApi';
import Modal from '@shared/components/Modal/Modal';
import Button from '@shared/components/Button/Button';
import styles from './Trash.module.css';
import '@features/files/styles/responsive.css';

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / 1024 ** exp;
    return `${value.toFixed(exp === 0 ? 0 : 1)} ${units[exp]}`;
}

function formatDate(isoString) {
    if (!isoString) return '—';
    return new Date(isoString).toLocaleDateString('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    });
}

function getFileTypeInfo(contentType, fileName = '') {
    const ext = fileName.split('.').pop()?.toUpperCase() || '';
    if (contentType?.includes('pdf') || ext === 'PDF') {
        return { label: 'PDF', icon: FileText, className: styles.typePdf };
    }
    if (contentType?.includes('image') || ['PNG', 'JPG', 'JPEG', 'WEBP', 'SVG'].includes(ext)) {
        return { label: ext || 'IMG', icon: ImageIcon, className: styles.typeImage };
    }
    if (contentType?.includes('word') || ['DOC', 'DOCX'].includes(ext)) {
        return { label: 'DOCX', icon: FileText, className: styles.typeDoc };
    }
    if (contentType?.includes('text') || ext === 'TXT') {
        return { label: 'TXT', icon: FileText, className: styles.typeTxt };
    }
    return { label: ext || 'FILE', icon: FileGenericIcon, className: styles.typeDefault };
}

/**
 * Página de Papelera con diseño de tabla estructurada, vaciado masivo y notificación flotante.
 */
export default function Trash() {
    const [trashedFiles, setTrashedFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [toast, setToast] = useState(null); // { message, type: 'success' | 'error' }
    const [busyId, setBusyId] = useState(null);
    const [emptyModalOpen, setEmptyModalOpen] = useState(false);
    const [deleteModalTarget, setDeleteModalTarget] = useState(null);
    const [emptying, setEmptying] = useState(false);

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
    };

    // Auto-ocultar toast después de 4 segundos
    useEffect(() => {
        if (!toast) return;
        const timer = setTimeout(() => setToast(null), 4000);
        return () => clearTimeout(timer);
    }, [toast]);

    const loadTrash = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const files = await transfersApi.listarPapelera();
            setTrashedFiles(Array.isArray(files) ? files : []);
        } catch {
            setError('No se pudo cargar la papelera. Inténtalo de nuevo.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadTrash();
    }, [loadTrash]);

    const handleRestore = async (file) => {
        setBusyId(file.id);
        try {
            await transfersApi.restaurar(file.id);
            showToast(`${file.original_name} restaurado correctamente.`, 'success');
            await loadTrash();
        } catch (err) {
            const detail = err.message || 'No se pudo restaurar el archivo.';
            showToast(`Error: ${detail}`, 'error');
        } finally {
            setBusyId(null);
        }
    };

    const handleConfirmSingleDelete = async () => {
        if (!deleteModalTarget) return;
        const file = deleteModalTarget;
        setBusyId(file.id);
        try {
            await transfersApi.eliminarDefinitivamente(file.id);
            showToast(`${file.original_name} eliminado definitivamente.`, 'success');
            setDeleteModalTarget(null);
            await loadTrash();
        } catch (err) {
            showToast(`Error: ${err.message || 'No se pudo eliminar el archivo.'}`, 'error');
        } finally {
            setBusyId(null);
        }
    };

    const handleEmptyTrash = async () => {
        setEmptying(true);
        try {
            await Promise.all(trashedFiles.map((f) => transfersApi.eliminarDefinitivamente(f.id)));
            showToast('Se vació la papelera correctamente.', 'success');
            setEmptyModalOpen(false);
            await loadTrash();
        } catch (err) {
            showToast(`Error al vaciar la papelera: ${err.message || 'Error desconocido'}`, 'error');
        } finally {
            setEmptying(false);
        }
    };

    return (
        <div className={styles.container}>
            <header className={styles.headerArea}>
                <div className={styles.headerText}>
                    <h1 className={styles.title}>Papelera</h1>
                    <p className={styles.subtitle}>
                        Los archivos eliminados se conservan aquí. Restáuralos o elimínalos definitivamente cuando ya no los necesites.
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

            {error && (
                <div className={styles.errorBanner} role="alert">
                    <span>{error}</span>
                    <button onClick={loadTrash} className={styles.retryBtn}>Reintentar</button>
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
                        {trashedFiles.map((file) => {
                            const isBusy = busyId === file.id;
                            const typeInfo = getFileTypeInfo(file.content_type, file.original_name);
                            const IconComponent = typeInfo.icon;

                            return (
                                <div key={file.id} className={styles.tableRow} data-table="row">
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
                                        {formatDate(file.trashed_at || file.updated_at)}
                                    </div>

                                    <div className={styles.cellSize} data-cell="size">
                                        {formatBytes(file.size_bytes)}
                                    </div>

                                    <div className={styles.cellActions} data-cell="actions">
                                        <button
                                            type="button"
                                            onClick={() => handleRestore(file)}
                                            className={styles.restoreBtn}
                                            title="Restaurar archivo"
                                            disabled={isBusy || emptying}
                                        >
                                            {isBusy ? (
                                                <Loader2 size={15} className={styles.spin} />
                                            ) : (
                                                <RotateCcw size={15} />
                                            )}
                                            <span>Restaurar</span>
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() => setDeleteModalTarget(file)}
                                            className={styles.deleteBtn}
                                            title="Eliminar definitivamente"
                                            disabled={isBusy || emptying}
                                        >
                                            {isBusy ? (
                                                <Loader2 size={15} className={styles.spin} />
                                            ) : (
                                                <Trash2 size={15} />
                                            )}
                                            <span>Eliminar</span>
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Modal de confirmación para eliminar un archivo individualmente */}
            {deleteModalTarget && (
                <Modal
                    open={Boolean(deleteModalTarget)}
                    onClose={() => !busyId && setDeleteModalTarget(null)}
                    title="Eliminar definitivamente"
                    icon={<AlertTriangle size={20} />}
                >
                    <div className={styles.modalBody}>
                        <p className={styles.modalText}>
                            ¿Estás seguro de que deseas eliminar permanentemente el archivo{' '}
                            <strong className={styles.fileNameHighlight}>"{deleteModalTarget.original_name}"</strong>?
                        </p>
                        <p className={styles.modalSubtext}>
                            Esta acción borrará el archivo físicamente del almacenamiento y liberará cuota. No se puede deshacer.
                        </p>
                        <div className={styles.modalActions}>
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={() => setDeleteModalTarget(null)}
                                disabled={Boolean(busyId)}
                            >
                                Cancelar
                            </Button>
                            <Button
                                type="button"
                                variant="danger"
                                onClick={handleConfirmSingleDelete}
                                loading={Boolean(busyId)}
                                loadingLabel="Eliminando..."
                            >
                                Eliminar definitivamente
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            {/* Modal de confirmación para vaciar la papelera */}
            {emptyModalOpen && (
                <Modal
                    open={emptyModalOpen}
                    onClose={() => !emptying && setEmptyModalOpen(false)}
                    title="Vaciar papelera"
                    icon={<AlertTriangle size={20} />}
                >
                    <div className={styles.modalBody}>
                        <p className={styles.modalText}>
                            ¿Estás seguro de que deseas eliminar definitivamente los{' '}
                            <strong>{trashedFiles.length} {trashedFiles.length === 1 ? 'archivo' : 'archivos'}</strong> que se encuentran en la papelera?
                        </p>
                        <p className={styles.modalSubtext}>
                            Todos los archivos se borrarán físicamente de manera permanente y se liberará su cuota de almacenamiento. Esta acción no se puede deshacer.
                        </p>
                        <div className={styles.modalActions}>
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={() => setEmptyModalOpen(false)}
                                disabled={emptying}
                            >
                                Cancelar
                            </Button>
                            <Button
                                type="button"
                                variant="danger"
                                onClick={handleEmptyTrash}
                                loading={emptying}
                                loadingLabel="Vaciando papelera..."
                            >
                                Vaciar toda la papelera
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            {/* Globo de notificación flotante (Esquina inferior derecha) */}
            {toast && (
                <div
                    className={`${styles.toast} ${toast.type === 'error' ? styles.toastError : styles.toastSuccess}`}
                    role="status"
                >
                    <span className={styles.toastMessage}>{toast.message}</span>
                    <button
                        type="button"
                        onClick={() => setToast(null)}
                        className={styles.toastCloseBtn}
                        aria-label="Cerrar notificación"
                    >
                        <X size={16} />
                    </button>
                </div>
            )}
        </div>
    );
}