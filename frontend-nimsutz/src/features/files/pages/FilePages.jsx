import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    Folder as FolderIcon,
    FolderPlus,
    Pencil,
    Trash2,
    Loader2,
    FileText,
    Image as ImageIcon,
    File as FileGenericIcon,
    X,
} from 'lucide-react';
import Button from '@shared/components/Button/Button';
import Badge from '@shared/components/Badge/Badge';
import { useFiles } from '../hooks/useFiles';
import { useTransfers } from '@features/files/transfers/hooks/useTransfers';
import FolderFormModal from '../components/FolderFormModal';
import ConfirmDialog from '../components/ConfirmDialog';
import UploadPanel from '@features/files/transfers/components/UploadPanel/UploadPanel';
import FileActions from '@features/files/transfers/components/FileActions/FileActions';
import styles from './FilePages.module.css';
import '@features/files/styles/responsive.css';

function formatBytes(bytes) {
    if (!bytes || bytes <= 0 || isNaN(Number(bytes))) return '0 B';
    const num = Number(bytes);
    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(Math.floor(Math.log(num) / Math.log(1024)), units.length - 1);
    if (exponent < 0) return '0 B';
    const value = num / 1024 ** exponent;
    return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function formatDate(isoString) {
    if (!isoString) return '—';
    try {
        const d = new Date(isoString);
        if (isNaN(d.getTime())) return '—';
        return d.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
        });
    } catch {
        return '—';
    }
}

function getFileTypeInfo(contentType, fileName = '') {
    const safeName = String(fileName || '');
    const ext = safeName.split('.').pop()?.toUpperCase() || '';
    const safeType = String(contentType || '').toLowerCase();

    if (safeType.includes('pdf') || ext === 'PDF') {
        return { label: 'PDF', icon: FileText, className: styles.typePdf };
    }
    if (safeType.includes('presentation') || ['PPT', 'PPTX'].includes(ext)) {
        return { label: ext || 'PPTX', icon: FileText, className: styles.typePpt };
    }
    if (safeType.includes('image') || ['PNG', 'JPG', 'JPEG', 'WEBP', 'SVG'].includes(ext)) {
        return { label: ext || 'IMG', icon: ImageIcon, className: styles.typeImage };
    }
    if (safeType.includes('word') || ['DOC', 'DOCX'].includes(ext)) {
        return { label: 'DOCX', icon: FileText, className: styles.typeDoc };
    }
    if (safeType.includes('spreadsheet') || ['XLS', 'XLSX', 'CSV'].includes(ext)) {
        return { label: ext || 'XLSX', icon: FileText, className: styles.typeExcel };
    }
    if (safeType.includes('zip') || ['ZIP', 'RAR', 'TAR', 'GZ'].includes(ext)) {
        return { label: ext || 'ZIP', icon: FileText, className: styles.typeZip };
    }
    return { label: ext || 'FILE', icon: FileGenericIcon, className: styles.typeDefault };
}

function buildBreadcrumb(folderIndex, folderId) {
    const path = [];
    let currentId = folderId;
    while (currentId != null) {
        const folder = folderIndex.get(currentId);
        if (!folder) break;
        path.unshift({ id: folder.id, name: folder.name });
        currentId = folder.parent;
    }
    return path;
}

export function FilesPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const folderIdParam = searchParams.get('folder');
    const folderId = folderIdParam ? Number(folderIdParam) : null;

    const {
        folders,
        files,
        folderIndex,
        loading,
        error,
        reload,
        createFolder,
        renameFolder,
        deleteFolder,
    } = useFiles(folderId);

    const { subirArchivo } = useTransfers();

    const breadcrumb = buildBreadcrumb(folderIndex, folderId);

    const [createOpen, setCreateOpen] = useState(false);
    const [renameTarget, setRenameTarget] = useState(null);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [uploadOpen, setUploadOpen] = useState(false);

    function openFolder(folder) {
        setSearchParams({ folder: String(folder.id) });
    }

    function goToRoot() {
        setSearchParams({});
    }

    function goToBreadcrumbIndex(index) {
        setSearchParams({ folder: String(breadcrumb[index].id) });
    }

    const safeFiles = Array.isArray(files) ? files : [];
    const safeFolders = Array.isArray(folders) ? folders : [];

    return (
        <section className={styles.page} aria-labelledby="files-title">
            <h1 id="files-title" className={styles.srOnly}>Mis archivos</h1>

            <nav aria-label="Ruta de carpetas" className={styles.breadcrumb} data-element="breadcrumb">
                <button type="button" className={styles.breadcrumbButton} onClick={goToRoot}>Raíz</button>
                {breadcrumb.map((crumb, index) => (
                    <span key={crumb.id}>
                        {' / '}
                        <button type="button" className={styles.breadcrumbButton} onClick={() => goToBreadcrumbIndex(index)}>
                            {crumb.name}
                        </button>
                    </span>
                ))}
            </nav>

            <div className={styles.toolbar} data-element="toolbar">
                <div className={styles.actions}>
                    <Button type="button" onClick={() => setCreateOpen(true)}>
                        <FolderPlus size={16} aria-hidden="true" /> Nueva carpeta
                    </Button>
                    {folderId != null && (
                        <Button type="button" onClick={() => setUploadOpen(true)}>
                            ↑ Subir archivo
                        </Button>
                    )}
                </div>
                {folderId == null && (
                    <Badge tone="info">Entra a una carpeta para subir archivos</Badge>
                )}
            </div>

            {error && (
                <p className={styles.banner} role="alert">
                    {error}
                </p>
            )}

            <div className={styles.tableCard}>
                <div className={styles.tableHeader} data-table="header">
                    <div className={styles.thName}>NOMBRE</div>
                    <div className={styles.thType}>TIPO</div>
                    <div className={styles.thSize}>TAMAÑO</div>
                    <div className={styles.thDate}>FECHA</div>
                    <div className={styles.thOwner}>PROPIETARIO</div>
                    <div className={styles.thStatus}>ESTADO</div>
                    <div className={styles.thActions}>ACCIONES</div>
                </div>

                {loading ? (
                    <div className={styles.emptyState}>
                        <Loader2 size={36} className={styles.spin} />
                        <p>Cargando explorador…</p>
                    </div>
                ) : folders.length === 0 && safeFiles.length === 0 ? (
                    <div className={styles.emptyState}>
                        <p>Esta carpeta está vacía.</p>
                    </div>
                ) : (
                    <div className={styles.tableBody}>
                        {/* Carpetas */}
                        {folders.map((folder) => (
                            <div key={`folder-${folder.id}`} className={styles.tableRow} data-table="row">
                                <div className={styles.cellName} data-cell="name">
                                    <button type="button" className={styles.folderBtn} onClick={() => openFolder(folder)}>
                                        <div className={styles.nameMeta}>
                                            <span className={styles.fileName}>{folder.name}</span>
                                            <span className={styles.fileSubtext}>Carpeta</span>
                                        </div>
                                    </button>
                                </div>
                                <div className={styles.cellType} data-cell="type">
                                    <div className={`${styles.iconBadge} ${styles.typeFolder}`}>
                                        <FolderIcon size={18} />
                                    </div>
                                </div>
                                <div className={styles.cellSize} data-cell="size">-</div>
                                <div className={styles.cellDate} data-cell="date">{formatDate(folder.updated_at)}</div>
                                <div className={styles.cellOwner} data-cell="owner">Pendiente</div>
                                <div className={styles.cellStatus} data-cell="status">-</div>
                                <div className={styles.cellActions} data-cell="actions">
                                    <button type="button" className={styles.linkAction} onClick={() => setRenameTarget(folder)} title="Renombrar">
                                        <Pencil size={18} />
                                    </button>
                                    <button type="button" className={styles.dangerAction} onClick={() => setDeleteTarget(folder)} title="Eliminar">
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            </div>
                        ))}

                        {/* Archivos reales */}
                        {safeFiles.map((file) => {
                            const typeInfo = getFileTypeInfo(file.content_type, file.original_name);
                            return (
                                <div key={`file-${file.id}`} className={styles.tableRow} data-table="row">
                                    <div className={styles.cellName} data-cell="name">
                                        <div className={styles.nameMeta}>
                                            <span className={styles.fileName} title={file.original_name}>
                                                {file.original_name}
                                            </span>
                                            <span className={styles.fileSubtext}>
                                                {folderId ? breadcrumb[breadcrumb.length - 1]?.name || 'Carpeta' : 'Raíz'}
                                            </span>
                                        </div>
                                    </div>
                                    <div className={styles.cellType} data-cell="type">
                                        <div className={`${styles.iconBadge} ${typeInfo.className}`}>
                                            {typeInfo.label}
                                        </div>
                                    </div>
                                    <div className={styles.cellSize} data-cell="size">{formatBytes(file.size_bytes)}</div>
                                    <div className={styles.cellDate} data-cell="date">{formatDate(file.updated_at)}</div>
                                    <div className={styles.cellOwner} data-cell="owner">Pendiente</div>
                                    <div className={styles.cellStatus} data-cell="status">
                                        <span className={`${styles.statusBadge} ${styles.statusDisponible}`}>
                                            <span className={styles.statusDot}></span>
                                            Disponible
                                        </span>
                                    </div>
                                    <div className={styles.cellActions} data-cell="actions">
                                        <FileActions file={file} onChanged={reload} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            <FolderFormModal open={createOpen} onClose={() => setCreateOpen(false)} onSubmit={(name) => createFolder(name)} />
            <FolderFormModal open={Boolean(renameTarget)} onClose={() => setRenameTarget(null)} folder={renameTarget} onSubmit={(name) => renameFolder(renameTarget.id, name)} />
            <ConfirmDialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)} title="Eliminar carpeta" description={`Esta acción no se puede deshacer. La carpeta "${deleteTarget?.name}" debe estar vacía.`} onConfirm={() => deleteFolder(deleteTarget.id)} />
            {uploadOpen && (
                <UploadPanel folderId={folderId} onCompleted={reload} onClose={() => setUploadOpen(false)} />
            )}
        </section>
    );
}
